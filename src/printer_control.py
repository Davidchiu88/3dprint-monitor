"""
Printer Control — send commands and upload files to printers.
Bambu: MQTT (already connected) + FTP upload (port 990)
K1C:  WebSocket commands + HTTP upload (/upload/filename)
"""

import asyncio
import ftplib
import io
import json
import logging
import ssl
import threading
import time
from typing import Any, Dict, List, Optional

import requests
import websockets

logger = logging.getLogger(__name__)


# ── Shared: Implicit TLS FTP client with PASV fix ────────────────────────
# Bambu printers use implicit TLS FTP (port 990) and return 0.0.0.0 in
# PASV responses — override makepasv() to substitute the real printer IP.

def _make_bambu_ftp_context() -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
    ctx.set_ciphers("ALL:@SECLEVEL=0")
    return ctx


class _ImplicitFTP_TLS(ftplib.FTP_TLS):
    """FTP over implicit TLS (port 990) with PASV 0.0.0.0 fix."""

    def __init__(self, printer_ip: str, **kwargs):
        self._printer_ip = printer_ip
        ctx = kwargs.pop("context", None) or _make_bambu_ftp_context()
        super().__init__(context=ctx, **kwargs)

    def connect(self, host="", port=0, timeout=-999, source_address=None):
        """Wrap socket with TLS immediately (implicit FTPS on port 990).
        Must set self.host so data-channel TLS uses correct server_hostname.
        """
        if not port:
            port = 990
        if host:
            self.host = host          # ← critical: FTP_TLS.ntransfercmd uses self.host
        self.source_address = source_address
        t = (self.timeout if self.timeout != -999 else 10) if timeout == -999 else timeout
        import socket as _s
        raw = _s.create_connection((host or self.host, port), t, source_address)
        self.sock = self.context.wrap_socket(raw, server_hostname=self.host)
        self.af = self.sock.family
        self.file = self.sock.makefile("r", encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome

    def makepasv(self):
        """Fix Bambu's PASV returning 0.0.0.0 — substitute real printer IP."""
        host, port = super().makepasv()
        if host in ("0.0.0.0", "127.0.0.1"):
            host = self._printer_ip
        return host, port


# ── K1C Controller ──────────────────────────────────────────────────────

class K1CController:
    TIMEOUT = 6

    def __init__(self, ip: str):
        self.ip = ip
        self.ws_url = f"ws://{ip}:9999"

    def _run(self, coro):
        """Run async coroutine synchronously."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    async def _send_cmd(self, msg: Dict) -> Optional[Dict]:
        """Connect, send command, optionally wait for response."""
        async with websockets.connect(
            self.ws_url, ping_interval=None, open_timeout=5, close_timeout=3
        ) as ws:
            await ws.send(json.dumps(msg))
            # Wait briefly for ack
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=3)
                return json.loads(raw)
            except asyncio.TimeoutError:
                return None

    async def _get_files(self) -> List[Dict]:
        """Request file list and parse retGcodeFileInfo messages.
        K1C response format:
          retGcodeFileInfo: {"totalNum": 33, "fileInfo": "FOLDER:FILENAME:SIZE:LAYER_H..."}
        One message per file.
        """
        files = []
        total = None
        async with websockets.connect(
            self.ws_url, ping_interval=None, open_timeout=5
        ) as ws:
            await ws.send(json.dumps({"method": "get", "params": {"reqGcodeFile": 1}}))
            # Collect for up to 4 seconds - K1C sends files one by one
            idle_count = 0
            for _ in range(200):   # 200 × 0.05 s = 10 s max
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.05)
                    idle_count = 0
                    data = json.loads(raw)
                    info = data.get("retGcodeFileInfo")
                    if not info:
                        continue
                    if total is None:
                        total = info.get("totalNum", 0)

                    file_str = info.get("fileInfo", "")
                    if file_str:
                        parts = file_str.split(":")
                        folder   = parts[0] if len(parts) > 0 else ""
                        filename = parts[1] if len(parts) > 1 else file_str
                        size     = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
                        path     = f"{folder}/{filename}" if folder else filename
                        if not any(f["name"] == filename for f in files):
                            files.append({"name": filename, "size": size,
                                          "path": path, "folder": folder})
                    if total is not None and len(files) >= total:
                        break
                except asyncio.TimeoutError:
                    idle_count += 1
                    # If nothing new for 1 second and we have files, stop
                    if idle_count >= 20 and files:
                        break
        return files

    # ── public API ────────────────────────────────────────────────────

    def pause(self) -> bool:
        try:
            self._run(self._send_cmd({"method": "set", "params": {"pause": 1}}))
            return True
        except Exception as e:
            logger.error(f"K1C pause error: {e}")
            return False

    def resume(self) -> bool:
        try:
            self._run(self._send_cmd({"method": "set", "params": {"pause": 0}}))
            return True
        except Exception as e:
            logger.error(f"K1C resume error: {e}")
            return False

    def stop(self) -> bool:
        try:
            self._run(self._send_cmd({"method": "set", "params": {"stop": 1}}))
            return True
        except Exception as e:
            logger.error(f"K1C stop error: {e}")
            return False

    def start_print(self, path: str) -> bool:
        """path = e.g. '/usr/data/printer_data/gcodes/myfile.gcode' or 'myfile.gcode'"""
        try:
            # Format: printprt:PATH/FILENAME or printprt:FILENAME
            if "/" not in path:
                path = "/usr/data/printer_data/gcodes/" + path
            folder = path.rsplit("/", 1)[0]
            filename = path.rsplit("/", 1)[1]
            cmd = f"printprt:{folder}/{filename}"
            self._run(self._send_cmd({"method": "set", "params": {"opGcodeFile": cmd}}))
            return True
        except Exception as e:
            logger.error(f"K1C start_print error: {e}")
            return False

    def list_files(self) -> List[Dict]:
        """List gcode files from K1C.
        Uses WebSocket reqGcodeFile (gets ALL files including newly uploaded ones
        without thumbnails). Falls back to HTTP thumbnail listing if WS fails.
        """
        import re, asyncio as _aio

        folder = "/usr/data/printer_data/gcodes"

        # ── Primary: HTTP thumbnail listing (fast, reliable) ──
        # New uploads may not have thumbnails yet → supplemented by WS check
        # ── Also run quick WS scan to catch recently uploaded files without thumbnail ──
        try:
            r = requests.get(f"http://{self.ip}/downloads/humbnail/", timeout=5)
            r.raise_for_status()
            thumbs = re.findall(r'href="([^"./][^"]*\.png)"', r.text)
            files = []
            for thumb_name in thumbs:
                base      = thumb_name[:-4]
                gcode_name = base + ".gcode"
                files.append({
                    "name":      gcode_name,
                    "size":      0,
                    "path":      f"{folder}/{gcode_name}",
                    "folder":    folder,
                    "thumbnail": f"http://{self.ip}/downloads/humbnail/{thumb_name}",
                })
            return files
        except Exception as e:
            logger.error(f"K1C list_files error: {e}")
            # Fallback to WS method
            try:
                return self._run(self._get_files())
            except Exception:
                return []

    def upload_file(self, filename: str, data: bytes) -> bool:
        """Upload via HTTP POST /upload/filename.
        K1C only accepts uploads in IDLE state.
        If PAUSED at 100%, auto-clear the job first.
        """
        # No pre-check needed: K1C will reject the upload itself if not ready

        try:
            # K1C upload rules:
            # - No leading underscore  (_file.gcode → file.gcode)
            # - No spaces             (my file.gcode → my_file.gcode)
            import re as _re
            safe_name = filename.replace(" ", "_")           # spaces → underscore
            safe_name = _re.sub(r'^[_\-\.]+', '', safe_name)  # strip leading _-.
            if not safe_name:
                safe_name = "upload.gcode"

            # K1C requires browser-like User-Agent to accept uploads
            url = f"http://{self.ip}/upload/{safe_name}"
            r = requests.post(
                url,
                files={"file": (safe_name, data, "application/octet-stream")},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "Referer":    f"http://{self.ip}/",
                    "Origin":     f"http://{self.ip}",
                    "Accept":     "application/json, text/plain, */*",
                },
                timeout=120
            )
            result = r.json()
            if result.get("code") == 200:
                if safe_name != filename:
                    logger.info(f"K1C upload: renamed '{filename}' → '{safe_name}'")
                return True
            logger.error(f"K1C upload returned code={result.get('code')}")
            return False
        except Exception as e:
            logger.error(f"K1C upload error: {e}")
            return False

    # K1C SSH credentials (root access via Dropbear SSH)
    SSH_USER = "root"
    SSH_PASS = "creality_2023"

    def ssh_reachable(self) -> bool:
        """Fast check: is SSH port 22 open? (closed while K1C is printing)."""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            ok = (s.connect_ex((self.ip, 22)) == 0)
            s.close()
            return ok
        except Exception:
            return False

    def _ssh_connect(self):
        """Open an SSH client to the K1C (Dropbear 2019.78). Caller closes it."""
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            self.ip, port=22,
            username=self.SSH_USER, password=self.SSH_PASS,
            timeout=15, banner_timeout=15,
            look_for_keys=False, allow_agent=False,
            disabled_algorithms={"pubkeys": ["rsa-sha2-256", "rsa-sha2-512"]},
        )
        return ssh

    def _remote_gcode_path(self, filename: str) -> str:
        name = filename.split("/")[-1]
        if filename.startswith("/usr/data"):
            return filename
        return f"/usr/data/printer_data/gcodes/{name}"

    def iter_download(self, filename: str):
        """Stream gcode bytes from K1C via SSH `cat` (yields ~64KB chunks).

        K1C downloads are slow (~150 KB/s, printer-CPU bound), so a 7 MB file
        takes ~50 s. Streaming keeps the HTTP connection fed so clients don't
        hit read-timeouts mid-transfer. Assumes ssh_reachable() is already true.
        """
        ssh = None
        try:
            ssh = self._ssh_connect()
            remote_path = self._remote_gcode_path(filename)
            _, stdout, _ = ssh.exec_command(f'cat "{remote_path}"')
            total = 0
            while True:
                chunk = stdout.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                yield chunk
            logger.info(f"K1C SSH stream done: {remote_path} ({total} bytes)")
        except Exception as e:
            logger.error(f"K1C SSH stream error: {e}")
        finally:
            if ssh:
                try: ssh.close()
                except Exception: pass

    def download_file(self, filename: str) -> Optional[bytes]:
        """Download gcode from K1C via SSH (Dropbear 2019.78, port 22).
        Credentials: root / creality_2023
        Falls back with diagnostics if SSH unavailable.
        """
        if not self.ssh_reachable():
            logger.warning(f"K1C ({self.ip}) SSH port 22 not reachable. Run: python tools/fix_k1c_black_ssh.py")
            return None

        ssh = None
        try:
            ssh = self._ssh_connect()
            remote_path = self._remote_gcode_path(filename)
            # Use cat via exec_command (SFTP fails on Dropbear 2019.78)
            _, stdout, stderr = ssh.exec_command(f'cat "{remote_path}"')
            data = stdout.read()
            err = stderr.read().decode(errors="replace").strip()
            if not data:
                raise Exception(f"Empty response: {err}")
            logger.info(f"K1C SSH download OK: {remote_path} ({len(data)} bytes)")
            return data
        except Exception as e:
            logger.error(f"K1C SSH download error: {e}")
            return None
        finally:
            if ssh:
                try: ssh.close()
                except Exception: pass

    def delete_file(self, path: str) -> bool:
        """Delete via WebSocket: deleteprt:FOLDER/FILENAME"""
        try:
            if "/" not in path:
                path = f"/usr/data/printer_data/gcodes/{path}"
            folder = path.rsplit("/", 1)[0]
            fname  = path.rsplit("/", 1)[1]
            cmd = f"deleteprt:{folder}/{fname}"
            self._run(self._send_cmd({"method": "set", "params": {"opGcodeFile": cmd}}))
            return True
        except Exception as e:
            logger.error(f"K1C delete error: {e}")
            return False

    def rename_file(self, path: str, new_name: str) -> bool:
        """Rename via WebSocket: renameprt:FULL_OLD_PATH:FULL_NEW_PATH
        Both paths must be complete. new_name can be just a filename or full path.
        """
        try:
            if "/" not in path:
                path = f"/usr/data/printer_data/gcodes/{path}"
            folder = path.rsplit("/", 1)[0]
            # If new_name is just a filename (no slash), prepend the same folder
            if "/" not in new_name:
                new_path = f"{folder}/{new_name}"
            else:
                new_path = new_name
            cmd = f"renameprt:{path}:{new_path}"
            self._run(self._send_cmd({"method": "set", "params": {"opGcodeFile": cmd}}))
            return True
        except Exception as e:
            logger.error(f"K1C rename error: {e}")
            return False


# ── Bambu Lab Controller ──────────────────────────────────────────────

class BambuController:
    def __init__(self, ip: str, device_id: str, access_code: str):
        self.ip = ip
        self.device_id = device_id
        self.access_code = access_code

    def _mqtt_send(self, payload: Dict) -> bool:
        """Open a quick MQTT connection and publish one message."""
        import paho.mqtt.client as mqtt

        done = threading.Event()
        ok = [False]

        def on_connect(c, u, f, rc, props=None):
            if rc == 0:
                topic = f"device/{self.device_id}/request"
                c.publish(topic, json.dumps(payload), qos=1)
                time.sleep(0.3)
                ok[0] = True
            done.set()

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        ctx.set_ciphers("ALL:@SECLEVEL=0")

        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ctrl")
        c.on_connect = on_connect
        c.tls_set_context(ctx)
        c.username_pw_set("bblp", self.access_code)

        try:
            c.connect(self.ip, 8883, keepalive=10)
            c.loop_start()
            done.wait(timeout=8)
            c.loop_stop()
            c.disconnect()
        except Exception as e:
            logger.error(f"Bambu MQTT error: {e}")
            return False
        return ok[0]

    # ── public API ────────────────────────────────────────────────────

    def pause(self) -> bool:
        return self._mqtt_send({"print": {"command": "pause", "sequence_id": "0"}})

    def resume(self) -> bool:
        return self._mqtt_send({"print": {"command": "resume", "sequence_id": "0"}})

    def stop(self) -> bool:
        return self._mqtt_send({"print": {"command": "stop", "sequence_id": "0"}})

    def start_print(self, filename: str) -> bool:
        """Start printing a file already on the printer.
        Uses full path if provided (e.g. /cache/file.gcode), otherwise
        falls back to /user/{filename} for X1/P1 compatibility.
        """
        if filename.startswith("/"):
            param = filename           # already a full path from FTP listing
        else:
            param = f"/user/{filename.split('/')[-1]}"
        return self._mqtt_send({
            "print": {
                "command": "gcode_file",
                "param": param,
                "sequence_id": "0",
            }
        })

    def _ftp_connect(self, timeout: int = 6) -> "_ImplicitFTP_TLS":
        """Open FTPS connection to this Bambu printer (port 990 with PASV fix)."""
        ftp = _ImplicitFTP_TLS(self.ip)
        ftp.connect(self.ip, 990, timeout=timeout)
        ftp.login("bblp", self.access_code)
        ftp.prot_p()
        return ftp

    def _ftp_available(self) -> bool:
        """Check port 990 is reachable (fast, non-blocking)."""
        import socket as _socket
        import select as _sel
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        s.setblocking(False)
        s.connect_ex((self.ip, 990))
        ok = bool(_sel.select([], [s], [s], 1.5)[1])
        s.close()
        return ok

    def list_files(self) -> List[Dict]:
        """List gcode files via FTPS (port 990) with PASV 0.0.0.0 fix.
        Bambu FTP root dirs: logger, recorder, cache, model, timelapse
        Gcode files are in /model (A1/A1 Mini) or /user (X1/P1 series).
        """
        if not self._ftp_available():
            return [{"_error": "no_ftp",
                     "_message": "FTP 未開放（印表機列印中時自動關閉）。\n"
                                 "在印表機空閒時切換至 LAN 模式即可啟用。"}]
        try:
            ftp = self._ftp_connect()
            files = []
            # Bambu FTP directory layout:
            # /       - root (same as /model on A1/A1 Mini)
            # /model  - cloud-synced .gcode.3mf files
            # /cache  - all files including recently sent ones
            # /user   - X1/P1 only (550 on A1/A1 Mini)
            for search_dir in ["/cache", "/model", "", "/user"]:
                try:
                    entries = ftp.nlst(search_dir) if search_dir else ftp.nlst()
                    for item in entries:
                        name = item.split("/")[-1]
                        if any(name.lower().endswith(ext)
                               for ext in (".gcode", ".3mf", ".bgcode")):
                            # Fix: if item has no dir prefix, prepend the search_dir
                            # (ftp.nlst sometimes returns bare filenames)
                            if item.startswith("/"):
                                path = item
                            elif "/" in item:
                                path = f"/{item}"
                            elif search_dir:
                                path = f"{search_dir}/{item}"
                            else:
                                path = f"/{item}"
                            files.append({"name": name, "size": 0, "path": path})
                    if files:
                        logger.info(f"Bambu FTP: found {len(files)} files in '{search_dir}'")
                        break
                except Exception:
                    continue

            # If no gcode found directly, try listing subdirectories
            if not files:
                try:
                    root_items = ftp.nlst()
                    for d in root_items:
                        try:
                            sub = ftp.nlst(d)
                            for item in sub:
                                name = item.split("/")[-1]
                                if any(name.lower().endswith(ext)
                                       for ext in (".gcode", ".3mf", ".bgcode")):
                                    files.append({"name": name, "size": 0,
                                                  "path": item if item.startswith("/") else f"/{item}"})
                        except Exception:
                            continue
                except Exception:
                    pass

            try: ftp.quit()
            except: pass
            return files if files else [{"_error": "no_files",
                                         "_message": "FTP 連線成功但未找到 gcode 檔案。\n"
                                                     "請確認印表機上已有切片檔案。"}]
        except Exception as e:
            logger.error(f"Bambu list_files error: {e}")
            return [{"_error": "ftp_error", "_message": str(e)}]

    def download_file(self, filename: str) -> Optional[bytes]:
        """Download file via FTPS."""
        try:
            ftp = self._ftp_connect(timeout=30)
            name = filename.split("/")[-1]
            buf = io.BytesIO()
            # Try paths in priority order
            paths_to_try = []
            if filename.startswith("/cache/") or filename.startswith("/user/") or filename.startswith("/model/"):
                paths_to_try = [filename]                     # already has correct dir
            elif filename.startswith("/"):
                # Path like "/filename" - missing dir prefix, try common dirs
                paths_to_try = [f"/cache{filename}", f"/model{filename}", filename]
            else:
                paths_to_try = [f"/cache/{name}", f"/model/{name}", f"/user/{name}"]

            downloaded = False
            last_err = None
            for p in paths_to_try:
                try:
                    ftp.retrbinary(f"RETR {p}", buf.write)
                    downloaded = True
                    logger.info(f"Bambu download OK: {p}")
                    break
                except Exception as e:
                    last_err = e
                    buf = io.BytesIO()  # reset buffer
                    continue
            if not downloaded:
                raise Exception(f"All paths failed: {last_err}")
            ftp.quit()
            return buf.getvalue()
        except Exception as e:
            logger.error(f"Bambu download error: {e}")
            return None

    def delete_file(self, path: str) -> bool:
        """Delete file via FTPS."""
        try:
            ftp = self._ftp_connect()
            name = path.split("/")[-1]
            ftp.delete(f"/user/{name}")
            ftp.quit()
            return True
        except Exception as e:
            logger.error(f"Bambu delete error: {e}")
            return False

    def rename_file(self, path: str, new_name: str) -> bool:
        """Rename file via FTPS."""
        try:
            ftp = self._ftp_connect()
            old_name = path.split("/")[-1]
            ftp.rename(f"/user/{old_name}", f"/user/{new_name}")
            ftp.quit()
            return True
        except Exception as e:
            logger.error(f"Bambu rename error: {e}")
            return False

    def upload_file(self, filename: str, data: bytes,
                    local_server_ip: str = "", local_server_port: int = 7000) -> bool:
        """Upload file to Bambu printer.

        Strategy:
        1. Try FTP STOR to /cache (correct path for A1/A1 Mini)
        2. If FTP fails → HTTP Pull: serve file from local API server,
           send MQTT project_file with http:// URL

        Args:
            local_server_ip: IP of this PC on the local network (for HTTP pull)
            local_server_port: Port of the API server (default 7000)
        """
        import hashlib, time as _t

        name = filename.split("/")[-1]
        md5 = hashlib.md5(data).hexdigest()

        # ── Method 1: FTP STOR (only if port 990 open AND STOR works) ────────
        # Note: China-version A1/A1 Mini FTP is read-only (STOR returns 550).
        # This method only succeeds for X1C, X1, P1P, P1S with writable FTP.
        ftp_ok = False
        if self._ftp_available():
            try:
                ftp = self._ftp_connect(timeout=4)  # Fast fail on China A1/A1 Mini
                ftp.storbinary(f"STOR /cache/{name}", io.BytesIO(data))
                logger.info(f"Bambu FTP upload OK: /cache/{name}")
                ftp_ok = True
                try: ftp.quit()
                except: pass
            except Exception as e:
                logger.debug(f"Bambu FTP upload not available: {e}")
                try:
                    if 'ftp' in dir(): ftp.close()
                except: pass

        if ftp_ok:
            return True

        # ── Method 2: HTTP Pull (serve from local API, printer downloads) ──
        if local_server_ip:
            try:
                # Save to temp dir
                from pathlib import Path as _P
                tmp = _P("data/tmp")
                tmp.mkdir(parents=True, exist_ok=True)
                tmp_file = tmp / name
                tmp_file.write_bytes(data)

                url = f"http://{local_server_ip}:{local_server_port}/api/tmp/{name}"
                logger.info(f"Bambu HTTP pull: {url}")

                # Send MQTT project_file command
                ok = self._mqtt_send({
                    "print": {
                        "sequence_id": "0",
                        "command": "project_file",
                        "param": "Metadata/plate_1.gcode",
                        "project_id": "0",
                        "profile_id": "0",
                        "task_id": "0",
                        "subtask_id": "0",
                        "file": "",
                        "url": url,
                        "md5": md5,
                        "timelapse": False,
                        "bed_type": "auto",
                        "bed_levelling": True,
                        "flow_cali": False,
                        "vibration_cali": False,
                        "layer_inspect": False,
                        "ams_mapping": "",
                        "use_ams": False,
                    }
                })

                # Keep temp file for 5 minutes then clean up
                def _cleanup():
                    _t.sleep(300)
                    try: tmp_file.unlink()
                    except: pass
                import threading
                threading.Thread(target=_cleanup, daemon=True).start()

                return ok
            except Exception as e:
                logger.error(f"Bambu HTTP pull failed: {e}")

        logger.warning(f"Bambu upload: all methods failed for {name}")
        return False
