"""
Camera capture + Google Drive sync module.

Supports:
  - K1C: HTTP MJPG snapshot from port 8080
  - Bambu A1/A1 Mini: Not supported locally (cloud only)

Google Drive upload via Google Apps Script webhook.
"""

import base64
import json
import logging
import socket
import ssl
import struct
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# ── Camera capture ─────────────────────────────────────────────────────

def capture_k1c_snapshot(ip: str, timeout: int = 5) -> Optional[bytes]:
    """Capture JPEG snapshot from K1C MJPG-Streamer (port 8080)."""
    try:
        r = requests.get(f"http://{ip}:8080/?action=snapshot",
                         timeout=timeout, stream=False)
        r.raise_for_status()
        if r.headers.get("content-type", "").startswith("image/"):
            return r.content
    except Exception as e:
        logger.error(f"K1C snapshot error ({ip}): {e}")
    return None


def capture_bambu_snapshot(ip: str, access_code: str, timeout: int = 20) -> Optional[bytes]:
    """
    Capture JPEG snapshot from Bambu Lab printers via port 6000 (JPEG frame stream).
    Supports: A1, A1 Mini, P1P, P1S, X1C (all models with local LAN mode).

    Protocol:
      1. TLS connect to port 6000
      2. Send 80-byte auth packet: [4B 0x40][4B 0x3000][4B 0][4B 0][32B bblp][32B access_code]
      3. Read 16-byte frame header: [4B payload_size][12B metadata]
      4. Read payload_size bytes = JPEG image
    """
    def make_auth(user: str, pw: str) -> bytes:
        pkt = bytearray(80)
        struct.pack_into('<I', pkt,  0, 0x40)
        struct.pack_into('<I', pkt,  4, 0x3000)
        struct.pack_into('<I', pkt,  8, 0)
        struct.pack_into('<I', pkt, 12, 0)
        u = user.encode()[:32]; pkt[16:16+len(u)] = u
        p = pw.encode()[:32];   pkt[48:48+len(p)] = p
        return bytes(pkt)

    def recv_exact(sock, n: int) -> bytes:
        buf = b''
        while len(buf) < n:
            chunk = sock.recv(min(65536, n - len(buf)))
            if not chunk:
                raise ConnectionError("Connection closed")
            buf += chunk
        return buf

    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        tls = ctx.wrap_socket(sock, server_hostname=ip)
        tls.connect((ip, 6000))
        tls.send(make_auth('bblp', access_code))

        # Read frame header + payload
        header = recv_exact(tls, 16)
        payload_size = struct.unpack_from('<I', header, 0)[0]
        if payload_size == 0 or payload_size > 10_000_000:
            logger.warning(f"Bambu camera: unusual payload size {payload_size}")
            return None
        payload = recv_exact(tls, payload_size)
        tls.close()

        if payload[:2] == b'\xff\xd8':
            return payload
        logger.warning(f"Bambu camera: not a JPEG (starts with {payload[:4].hex()})")
        return None
    except Exception as e:
        logger.error(f"Bambu camera error ({ip}): {e}")
        return None


def get_snapshot_url_k1c(ip: str) -> str:
    """Return the direct snapshot URL for K1C (for browser display)."""
    return f"http://{ip}:8080/?action=snapshot"


def get_stream_url_k1c(ip: str) -> str:
    """Return the MJPG stream URL for K1C (for browser <img> or VLC)."""
    return f"http://{ip}:8080/?action=stream"


# ── Google Drive upload ────────────────────────────────────────────────

def upload_to_drive(
    gscript_url: str,
    printer_name: str,
    filename: str,
    data: bytes,
    mime_type: str = "image/jpeg",
    file_type: str = "snapshot",
    metadata: Optional[Dict] = None,
    timeout: int = 30,
) -> Optional[Dict]:
    """Upload file to Google Drive via Google Apps Script webhook."""
    if not gscript_url:
        logger.warning("No Google Apps Script URL configured")
        return None
    try:
        payload = {
            "type":         file_type,
            "printer_name": printer_name,
            "filename":     filename,
            "data":         base64.b64encode(data).decode(),
            "mime_type":    mime_type,
            "timestamp":    datetime.now().isoformat(),
            "metadata":     metadata or {},
        }
        r = requests.post(gscript_url, json=payload, timeout=timeout)
        result = r.json()
        if result.get("ok"):
            logger.info(f"Drive upload OK: {filename} → {result.get('folder','')}")
        else:
            logger.warning(f"Drive upload failed: {result.get('error','?')}")
        return result
    except Exception as e:
        logger.error(f"Drive upload error: {e}")
        return None


# ── Drive file sync (K1C gcode files) ──────────────────────────────────

def sync_k1c_files_to_drive(
    ip: str,
    printer_name: str,
    gscript_url: str,
    data_dir: str = "data",
    force: bool = False,
) -> Dict:
    """Download gcode files from K1C and upload to Google Drive."""
    import re
    results = {"uploaded": [], "skipped": [], "errors": []}

    # Track which files were already synced
    sync_state_file = Path(data_dir) / "drive_sync_state.json"
    state: Dict = {}
    if sync_state_file.exists():
        try:
            state = json.loads(sync_state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    printer_state = state.get(printer_name, {})

    # Get file list via HTTP directory listing
    try:
        html = requests.get(f"http://{ip}/downloads/humbnail/", timeout=5).text
        thumb_files = re.findall(r'href="([^"./][^"]*\.png)"', html)
    except Exception as e:
        logger.error(f"Cannot list K1C files: {e}")
        results["errors"].append(str(e))
        return results

    for thumb in thumb_files:
        gcode_name = thumb[:-4] + ".gcode"  # strip .png

        # Skip if already synced (check by name)
        if not force and printer_state.get(gcode_name, {}).get("synced"):
            results["skipped"].append(gcode_name)
            continue

        # Download gcode
        try:
            r = requests.get(
                f"http://{ip}/downloads/original/{gcode_name}",
                timeout=60, stream=True
            )
            if r.status_code == 404:
                # Try without .gcode (some filenames don't have extension in URL)
                r = requests.get(f"http://{ip}/downloads/original/{thumb[:-4]}", timeout=60)

            r.raise_for_status()
            gcode_data = r.content
        except Exception as e:
            logger.warning(f"Skip {gcode_name}: {e}")
            results["errors"].append(f"{gcode_name}: {e}")
            continue

        # Upload to Drive
        result = upload_to_drive(
            gscript_url=gscript_url,
            printer_name=printer_name,
            filename=gcode_name,
            data=gcode_data,
            mime_type="application/octet-stream",
            file_type="gcode",
            metadata={"printer": printer_name, "source": f"http://{ip}"},
        )

        if result and result.get("ok"):
            printer_state[gcode_name] = {
                "synced":    True,
                "synced_at": datetime.now().isoformat(),
                "drive_url": result.get("url", ""),
                "size":      len(gcode_data),
            }
            results["uploaded"].append(gcode_name)
        else:
            results["errors"].append(f"{gcode_name}: upload failed")

    # Save state
    state[printer_name] = printer_state
    sync_state_file.parent.mkdir(parents=True, exist_ok=True)
    sync_state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"{printer_name} sync: {len(results['uploaded'])} uploaded, "
                f"{len(results['skipped'])} skipped, {len(results['errors'])} errors")
    return results


# ── Scheduled snapshot task ────────────────────────────────────────────

class CameraScheduler:
    """
    Periodically capture snapshots and save to disk + optionally upload to Drive.
    Saves to: data/snapshots/{printer_name}/{YYYY-MM-DD}/{HH-MM-SS}.jpg
    """

    def __init__(
        self,
        printers_config: List[Dict],
        gscript_url: str = "",
        snapshot_interval_min: int = 30,
        data_dir: str = "data",
        keep_days: int = 7,          # auto-delete snapshots older than N days
    ):
        self.printers_config = printers_config
        self.gscript_url = gscript_url
        self.interval_sec = snapshot_interval_min * 60
        self.data_dir = Path(data_dir)
        self.keep_days = keep_days
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.last_snapshots: Dict[str, bytes] = {}
        self.last_snapshot_time: Dict[str, str] = {}

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="camera-scheduler"
        )
        self._thread.start()
        logger.info(f"Camera scheduler started (interval={self.interval_sec//60}min)")

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        # Delay initial capture by 30s to let monitors connect first
        self._stop.wait(30)
        if self._stop.is_set():
            return
        self._capture_all()
        while not self._stop.is_set():
            self._stop.wait(self.interval_sec)
            if not self._stop.is_set():
                self._capture_all()
                self._cleanup_old()

    def _capture_all(self) -> None:
        for pc in self.printers_config:
            name  = pc.get("name", "")
            ptype = pc.get("type", "")
            ip    = pc.get("ip", "")
            if not ip or not name:
                continue
            try:
                img = None
                if "creality" in ptype:
                    img = capture_k1c_snapshot(ip)
                elif "bambu" in ptype:
                    code = pc.get("access_code", "")
                    if code:
                        img = capture_bambu_snapshot(ip, code)
                if img:
                    self._save_snapshot(name, img)
                    if self.gscript_url:
                        self._upload_snapshot(name, img)
            except Exception as e:
                logger.error(f"Snapshot error {name}: {e}")

    def _save_snapshot(self, name: str, img: bytes) -> Path:
        """Save JPEG to data/snapshots/{name}/{date}/{time}.jpg"""
        now = datetime.now()
        safe = name.replace(" ", "_").replace("/", "-")
        snap_dir = self.data_dir / "snapshots" / safe / now.strftime("%Y-%m-%d")
        snap_dir.mkdir(parents=True, exist_ok=True)
        path = snap_dir / f"{now.strftime('%H-%M-%S')}.jpg"
        path.write_bytes(img)
        # Keep reference in memory
        self.last_snapshots[name] = img
        self.last_snapshot_time[name] = now.isoformat()
        logger.info(f"Snapshot saved: {path.relative_to(self.data_dir)} ({len(img)//1024}KB)")
        return path

    def _upload_snapshot(self, name: str, img: bytes) -> None:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe = name.replace(" ", "_")
        upload_to_drive(
            gscript_url=self.gscript_url,
            printer_name=name,
            filename=f"{safe}_{ts}.jpg",
            data=img,
            mime_type="image/jpeg",
            file_type="snapshot",
            metadata={"printer": name, "time": ts},
        )

    def _cleanup_old(self) -> None:
        """Delete snapshots older than keep_days."""
        import shutil
        cutoff = datetime.now().timestamp() - self.keep_days * 86400
        snap_root = self.data_dir / "snapshots"
        if not snap_root.exists():
            return
        for printer_dir in snap_root.iterdir():
            for date_dir in printer_dir.iterdir():
                if date_dir.is_dir() and date_dir.stat().st_mtime < cutoff:
                    shutil.rmtree(date_dir, ignore_errors=True)
                    logger.debug(f"Deleted old snapshots: {date_dir}")

    def list_snapshots(self, printer_name: str, limit: int = 48) -> List[Dict]:
        """List saved snapshot files for a printer, newest first."""
        safe = printer_name.replace(" ", "_").replace("/", "-")
        snap_root = self.data_dir / "snapshots" / safe
        if not snap_root.exists():
            return []
        files = sorted(snap_root.rglob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)
        result = []
        for f in files[:limit]:
            result.append({
                "path":      str(f.relative_to(self.data_dir)),
                "timestamp": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "size":      f.stat().st_size,
            })
        return result

    def get_snapshot(self, printer_name: str) -> Optional[bytes]:
        return self.last_snapshots.get(printer_name)

    def force_capture(self, printer_name: str) -> Optional[bytes]:
        """Immediate capture for a specific printer."""
        for pc in self.printers_config:
            if pc.get("name") != printer_name:
                continue
            ip    = pc.get("ip", "")
            ptype = pc.get("type", "")
            try:
                if "creality" in ptype:
                    img = capture_k1c_snapshot(ip)
                elif "bambu" in ptype:
                    img = capture_bambu_snapshot(ip, pc.get("access_code", ""))
                else:
                    return None
                if img:
                    self._save_snapshot(printer_name, img)
                return img
            except Exception as e:
                logger.error(f"Force capture error {printer_name}: {e}")
                return None
        return None
