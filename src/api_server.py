"""
Local API server — serves printer status, history and profiles.
Run: uvicorn src.api_server:app --host 0.0.0.0 --port 7000
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Query, Body, UploadFile, File, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="3D Printer Monitor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["*"],
)

STATUS_FILE   = Path("data/printer_status.json")
HISTORY_FILE  = Path("data/print_history.json")
PROFILES_FILE = Path("data/printer_profiles.json")


# ── helpers ─────────────────────────────────────────────────────────────

def _read_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Read {path}: {e}")
    return default

def _write_json(path: Path, data) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        logger.error(f"Write {path}: {e}")
        return False


# ── /api/status ──────────────────────────────────────────────────────────

@app.get("/api/status")
def get_status():
    data = _read_json(STATUS_FILE, {})
    return {"ok": True, "timestamp": datetime.now().isoformat(), "printers": data}


# ── /api/history ─────────────────────────────────────────────────────────

@app.get("/api/history")
def get_history(
    limit: int = Query(default=200, le=500),
    printer: Optional[str] = Query(default=None),
):
    records: List[Dict] = _read_json(HISTORY_FILE, [])

    # Merge active prints from status
    status = _read_json(STATUS_FILE, {})
    active = []
    for name, s in status.items():
        if (s.get("state") or "").upper() == "PRINTING" and s.get("print_file"):
            if printer and name != printer:
                continue
            extra = s.get("extra_data") or {}
            mats  = s.get("materials") or {}
            active.append({
                "id":               f"active-{name}",
                "printer_name":     name,
                "printer_type":     s.get("printer_type", ""),
                "file_name":        s.get("print_file", ""),
                "start_time":       s.get("timestamp", ""),
                "end_time":         None,
                "duration_sec":     None,
                "status":           "printing",
                "progress_at_end":  s.get("progress"),
                "filament_used_mm": extra.get("used_material_mm"),
                "materials":        mats,
                "thumbnail_url":    None,
                "extra":            {},
            })

    # Filter by printer name if requested
    if printer:
        records = [r for r in records if r.get("printer_name") == printer]

    combined = active + list(reversed(records[-limit:]))

    # Stats (global or per-printer)
    all_records = _read_json(HISTORY_FILE, [])
    if printer:
        all_records = [r for r in all_records if r.get("printer_name") == printer]

    stats = {
        "total":     len(all_records),
        "completed": sum(1 for r in all_records if r.get("status") == "completed"),
        "failed":    sum(1 for r in all_records if r.get("status") == "failed"),
        "active":    len(active),
        "total_print_hours": round(
            sum(r.get("duration_sec") or 0
                for r in all_records if r.get("status") == "completed") / 3600, 1
        ),
    }
    return {"ok": True, "records": combined[:limit], "stats": stats}


# ── /api/printers (profiles) ─────────────────────────────────────────────

_DEFAULT_PROFILE = {
    "display_name": "",
    "location":     "",
    "tasks":        [],
    "notes":        "",
    "color":        "",
    "enabled":      True,
}


def _get_profile(name: str, profiles: Dict) -> Dict:
    p = dict(_DEFAULT_PROFILE)
    p.update(profiles.get(name, {}))
    if not p["display_name"]:
        p["display_name"] = name
    return p


@app.get("/api/printers")
def get_printers():
    """Return merged printer status + profiles."""
    status   = _read_json(STATUS_FILE, {})
    profiles = _read_json(PROFILES_FILE, {})

    result = {}
    for name, s in status.items():
        profile = _get_profile(name, profiles)
        result[name] = {
            **s,
            "profile": profile,
        }
    # Also include printers in profiles that aren't in status
    for name, p in profiles.items():
        if name not in result:
            result[name] = {
                "name":         name,
                "online":       False,
                "state":        "OFFLINE",
                "printer_type": "",
                "profile":      _get_profile(name, profiles),
            }
    return {"ok": True, "printers": result}


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    location:     Optional[str] = None
    tasks:        Optional[List[str]] = None
    notes:        Optional[str] = None
    color:        Optional[str] = None
    enabled:      Optional[bool] = None


@app.put("/api/printers/{name}")
def update_printer_profile(name: str, body: ProfileUpdate):
    """Update editable fields for a printer profile."""
    profiles = _read_json(PROFILES_FILE, {})
    current  = _get_profile(name, profiles)
    update   = {k: v for k, v in body.model_dump().items() if v is not None}
    current.update(update)
    profiles[name] = current
    ok = _write_json(PROFILES_FILE, profiles)
    return {"ok": ok, "profile": current}


# ── /api/health ──────────────────────────────────────────────────────────


# ── helpers for control ──────────────────────────────────────────────────

def _get_controller(name: str):
    """Get the right controller for a printer by name.
    Uses YAML config as the authoritative source for type/ip/credentials,
    avoiding race conditions with the frequently-written status file.
    """
    from .printer_control import K1CController, BambuController

    try:
        import yaml
        cfg = yaml.safe_load(open("config/printers.yaml", encoding="utf-8"))
        for pc in cfg.get("printers", []):
            if pc.get("name") == name:
                ip    = pc.get("ip", "")
                ptype = pc.get("type", "")   # from config, not status file
                if "bambu" in ptype:
                    return BambuController(ip, pc.get("device_id", ""), pc.get("access_code", ""))
                elif "creality" in ptype:
                    return K1CController(ip)
    except Exception as e:
        logger.error(f"Failed to load config for {name!r}: {e}")
    return None


# ── /api/control ─────────────────────────────────────────────────────────

@app.post("/api/control/{name}/pause")
def control_pause(name: str):
    c = _get_controller(name)
    if not c:
        raise HTTPException(404, "Printer not found")
    ok = c.pause()
    return {"ok": ok, "action": "pause", "printer": name}


@app.post("/api/control/{name}/resume")
def control_resume(name: str):
    c = _get_controller(name)
    if not c:
        raise HTTPException(404, "Printer not found")
    ok = c.resume()
    return {"ok": ok, "action": "resume", "printer": name}


@app.post("/api/control/{name}/stop")
def control_stop(name: str):
    c = _get_controller(name)
    if not c:
        raise HTTPException(404, "Printer not found")
    ok = c.stop()
    return {"ok": ok, "action": "stop", "printer": name}


@app.post("/api/control/{name}/print")
def control_start_print(name: str, file: str = Query(..., description="filename or path to print")):
    c = _get_controller(name)
    if not c:
        raise HTTPException(404, "Printer not found")
    ok = c.start_print(file)
    return {"ok": ok, "action": "start_print", "file": file, "printer": name}


# ── /api/files ────────────────────────────────────────────────────────────

@app.get("/api/files/{name}")
def list_files(name: str):
    c = _get_controller(name)
    if not c:
        raise HTTPException(404, "Printer not found")
    files = c.list_files()
    return {"ok": True, "printer": name, "files": files}


def _get_local_ip() -> str:
    """Detect this machine's LAN IP address."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""


@app.post("/api/files/{name}")
async def upload_file(name: str, background_tasks: BackgroundTasks,
                      file: UploadFile = File(...),
                      request: Request = None):
    c = _get_controller(name)
    if not c:
        raise HTTPException(404, "Printer not found")
    data = await file.read()
    filename = file.filename

    # For K1C: direct HTTP upload (fast, sync)
    status = _read_json(STATUS_FILE, {})
    ptype = status.get(name, {}).get("printer_type", "")
    if "creality" in ptype:
        ok = c.upload_file(filename, data)
        return {"ok": ok, "filename": filename, "size": len(data), "printer": name}

    # For Bambu: run upload in background (avoids MQTT timeout blocking response)
    local_ip = _get_local_ip()

    def _do_upload():
        if hasattr(c, 'upload_file') and 'local_server_ip' in c.upload_file.__code__.co_varnames:
            result = c.upload_file(filename, data, local_server_ip=local_ip,
                                   local_server_port=7000)
        else:
            result = c.upload_file(filename, data)
        logger.info(f"Background upload {filename} → {name}: {result}")

    if background_tasks:
        background_tasks.add_task(_do_upload)
        return {"ok": True, "filename": filename, "size": len(data),
                "printer": name, "status": "uploading",
                "note": "Bambu HTTP pull 上傳已開始，印表機將自動下載並開始列印"}
    else:
        _do_upload()
        return {"ok": True, "filename": filename, "size": len(data), "printer": name}


@app.get("/api/files/{name}/download")
def download_file(name: str, file: str = Query(...)):
    from fastapi.responses import Response, StreamingResponse
    from urllib.parse import quote
    from .printer_control import K1CController

    c = _get_controller(name)
    if not c:
        raise HTTPException(404, "Printer not found")

    fname = file.split("/")[-1]
    # RFC 5987 — survives Chinese filenames in Content-Disposition
    disposition = f"attachment; filename*=UTF-8''{quote(fname)}"

    # K1C: stream via SSH. Downloads are slow (~150 KB/s, printer-CPU bound),
    # so a 7 MB file takes ~50 s. Streaming keeps the connection fed so the
    # client never read-times-out mid-transfer.
    if isinstance(c, K1CController):
        if not c.ssh_reachable():
            raise HTTPException(
                503,
                f"K1C SSH 服務不可用 ({c.ip}) — 列印中時 SSH 會自動關閉，"
                f"請待列印完成後再下載。",
            )
        return StreamingResponse(
            c.iter_download(file),
            media_type="application/octet-stream",
            headers={"Content-Disposition": disposition},
        )

    # Bambu: buffered download via FTP
    data = c.download_file(file)
    if data is None:
        raise HTTPException(
            500,
            "下載失敗 — 拓竹 FTP 需印表機空閒並切換至 LAN 模式（列印中會自動關閉）。",
        )
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": disposition},
    )


@app.delete("/api/files/{name}")
def delete_file(name: str, file: str = Query(...)):
    c = _get_controller(name)
    if not c:
        raise HTTPException(404, "Printer not found")
    ok = c.delete_file(file)
    return {"ok": ok, "deleted": file, "printer": name}



# ── /api/files/{name}/sync_all  (Download all → local disk) ───────────────

import threading as _threading

_sync_jobs: dict = {}   # job_id → {status, total, done, errors, path}

@app.post("/api/files/{name}/sync_all")
def sync_all_files(name: str, base_dir: str = Query(default=r"D:\印表機檔案")):
    """Download ALL printer files to base_dir\\name\\ on the server disk."""
    import uuid, time as _t
    job_id = str(uuid.uuid4())[:8]
    save_dir = Path(base_dir) / name
    save_dir.mkdir(parents=True, exist_ok=True)

    job = {"status": "running", "total": 0, "done": 0, "skipped": 0,
           "errors": [], "save_dir": str(save_dir), "current": ""}
    _sync_jobs[job_id] = job

    def _run():
        try:
            c = _get_controller(name)
            if not c:
                job["status"] = "error"; job["errors"].append("Printer not found"); return

            files_resp = c.list_files()
            files = [f for f in files_resp if not f.get("_error")]
            job["total"] = len(files)

            for f in files:
                fname = f.get("name", "")
                fpath = f.get("path", fname)
                dest  = save_dir / fname
                job["current"] = fname

                if dest.exists():
                    job["skipped"] += 1
                    job["done"] += 1
                    continue

                data = c.download_file(fpath)
                if data:
                    dest.write_bytes(data)
                    logger.info(f"Sync saved: {dest}")
                else:
                    job["errors"].append(f"Failed: {fname}")
                job["done"] += 1

            job["status"] = "done"
            job["current"] = ""
        except Exception as e:
            job["status"] = "error"
            job["errors"].append(str(e))

    t = _threading.Thread(target=_run, daemon=True)
    t.start()
    return {"ok": True, "job_id": job_id, "save_dir": str(save_dir)}


@app.get("/api/files/{name}/sync_all/{job_id}")
def sync_all_status(name: str, job_id: str):
    job = _sync_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    pct = round(job["done"] / job["total"] * 100) if job["total"] else 0
    return {"ok": True, **job, "pct": pct}


@app.put("/api/files/{name}/rename")
def rename_file(name: str, file: str = Query(...), new_name: str = Query(...)):
    c = _get_controller(name)
    if not c:
        raise HTTPException(404, "Printer not found")
    ok = c.rename_file(file, new_name)
    return {"ok": ok, "old": file, "new": new_name, "printer": name}


# ── /api/health ──────────────────────────────────────────────────────────


# ── /api/camera ────────────────────────────────────────────────────────

@app.get("/api/camera/{name}/snapshot")
def camera_snapshot(name: str):
    """Get camera snapshot — K1C via HTTP, Bambu via port 6000 JPEG stream."""
    from fastapi.responses import Response
    from .camera_sync import capture_k1c_snapshot, capture_bambu_snapshot

    status = _read_json(STATUS_FILE, {})
    s = status.get(name, {})
    ptype = s.get("printer_type", "")

    # Get IP and credentials from config
    try:
        import yaml
        cfg = yaml.safe_load(open("config/printers.yaml", encoding="utf-8"))
        pc  = next((p for p in cfg.get("printers", []) if p.get("name") == name), None)
    except Exception:
        pc = None

    if not pc:
        raise HTTPException(404, "Printer not found in config")

    ip = pc.get("ip", "")

    if "bambu" in ptype:
        code = pc.get("access_code", "")
        if not code:
            raise HTTPException(400, "access_code not configured")
        img = capture_bambu_snapshot(ip, code)
    else:
        img = capture_k1c_snapshot(ip)

    if img is None:
        raise HTTPException(503, "Camera capture failed")

    return Response(content=img, media_type="image/jpeg",
                    headers={"Cache-Control": "no-cache"})


@app.get("/api/camera/{name}/history")
def camera_history(name: str, limit: int = Query(default=48, le=200)):
    """List saved snapshots for a printer."""
    snap_dir = Path("data/snapshots") / name.replace(" ", "_").replace("/", "-")
    if not snap_dir.exists():
        return {"ok": True, "snapshots": [], "count": 0}
    files = sorted(snap_dir.rglob("*.jpg"),
                   key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    result = []
    for f in files:
        result.append({
            "path":      str(f.relative_to(Path("data"))),
            "timestamp": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            "size":      f.stat().st_size,
            "url":       f"/api/snapshots/{f.relative_to(Path('data/snapshots'))}",
        })
    return {"ok": True, "snapshots": result, "count": len(result)}


@app.get("/api/snapshots/{full_path:path}")
def serve_snapshot(full_path: str):
    """Serve a saved snapshot image."""
    from fastapi.responses import FileResponse
    path = Path("data/snapshots") / full_path
    if not path.exists() or not path.suffix == ".jpg":
        raise HTTPException(404, "Snapshot not found")
    return FileResponse(str(path), media_type="image/jpeg")


@app.get("/api/camera/{name}/stream_url")
def camera_stream_url(name: str):
    """Return the MJPG stream URL for a printer."""
    from .camera_sync import get_stream_url_k1c

    status = _read_json(STATUS_FILE, {})
    s = status.get(name, {})
    ptype = s.get("printer_type", "")

    if "bambu" in ptype:
        return {"ok": False, "supported": False,
                "error": "Bambu A1/A1 Mini 不支援本地攝影機存取"}

    try:
        import yaml
        cfg = yaml.safe_load(open("config/printers.yaml", encoding="utf-8"))
        ip = next((pc["ip"] for pc in cfg.get("printers", []) if pc.get("name") == name), None)
    except Exception:
        ip = None

    if not ip:
        raise HTTPException(404, "Printer not found")

    return {
        "ok": True,
        "supported": True,
        "stream_url": get_stream_url_k1c(ip),
        "snapshot_url": f"http://{ip}:8080/?action=snapshot",
        "mjpg_url": f"http://{ip}:8080/?action=stream",
    }


# ── /api/drive ─────────────────────────────────────────────────────────

DRIVE_CONFIG_FILE = Path("data/drive_config.json")


def _get_gscript_url() -> str:
    cfg = _read_json(DRIVE_CONFIG_FILE, {})
    return cfg.get("gscript_url", "")


class DriveConfigUpdate(BaseModel):
    gscript_url: str
    snapshot_interval_min: Optional[int] = 30


@app.get("/api/drive/config")
def get_drive_config():
    cfg = _read_json(DRIVE_CONFIG_FILE, {})
    return {"ok": True, "config": cfg}


@app.put("/api/drive/config")
def update_drive_config(body: DriveConfigUpdate):
    cfg = _read_json(DRIVE_CONFIG_FILE, {})
    cfg["gscript_url"] = body.gscript_url
    cfg["snapshot_interval_min"] = body.snapshot_interval_min or 30
    ok = _write_json(DRIVE_CONFIG_FILE, cfg)
    return {"ok": ok, "config": cfg}


@app.post("/api/drive/snapshot/{name}")
def drive_upload_snapshot(name: str):
    """Capture snapshot and upload to Google Drive immediately."""
    from .camera_sync import capture_k1c_snapshot, upload_to_drive
    from fastapi.concurrency import run_in_threadpool

    gscript_url = _get_gscript_url()
    if not gscript_url:
        raise HTTPException(400, "Google Drive 未設定（請先設定 GAS URL）")

    status = _read_json(STATUS_FILE, {})
    s = status.get(name, {})
    ptype = s.get("printer_type", "")

    if "bambu" in ptype:
        return {"ok": False, "error": "Bambu 不支援本地攝影機"}

    try:
        import yaml
        cfg = yaml.safe_load(open("config/printers.yaml", encoding="utf-8"))
        ip = next((pc["ip"] for pc in cfg.get("printers", []) if pc.get("name") == name), None)
    except Exception:
        ip = None

    if not ip:
        raise HTTPException(404, "Printer not found")

    img = capture_k1c_snapshot(ip)
    if not img:
        raise HTTPException(503, "Camera capture failed")

    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe = name.replace(" ", "_")
    result = upload_to_drive(
        gscript_url=gscript_url,
        printer_name=name,
        filename=f"{safe}_{ts}.jpg",
        data=img,
        mime_type="image/jpeg",
        file_type="snapshot",
        metadata={"printer": name, "time": ts},
    )
    return result or {"ok": False, "error": "Upload failed"}


@app.post("/api/drive/sync_files/{name}")
def drive_sync_files(name: str, force: bool = False):
    """Sync gcode files from K1C to Google Drive."""
    from .camera_sync import sync_k1c_files_to_drive

    gscript_url = _get_gscript_url()
    if not gscript_url:
        raise HTTPException(400, "Google Drive 未設定")

    status = _read_json(STATUS_FILE, {})
    s = status.get(name, {})
    ptype = s.get("printer_type", "")

    if "bambu" in ptype:
        return {"ok": False, "error": "Bambu 不支援本地檔案同步"}

    try:
        import yaml
        cfg = yaml.safe_load(open("config/printers.yaml", encoding="utf-8"))
        ip = next((pc["ip"] for pc in cfg.get("printers", []) if pc.get("name") == name), None)
    except Exception:
        ip = None

    if not ip:
        raise HTTPException(404, "Printer not found")

    result = sync_k1c_files_to_drive(ip, name, gscript_url, force=force)
    return {"ok": True, "printer": name, **result}


@app.post("/api/drive/sync_all")
def drive_sync_all(force: bool = False):
    """Sync all K1C printers to Google Drive."""
    from .camera_sync import sync_k1c_files_to_drive

    gscript_url = _get_gscript_url()
    if not gscript_url:
        raise HTTPException(400, "Google Drive 未設定")

    try:
        import yaml
        printers = yaml.safe_load(open("config/printers.yaml", encoding="utf-8")).get("printers", [])
    except Exception:
        raise HTTPException(500, "Config error")

    all_results = {}
    for pc in printers:
        if "creality" in pc.get("type", ""):
            name = pc["name"]
            ip   = pc.get("ip", "")
            if ip:
                all_results[name] = sync_k1c_files_to_drive(ip, name, gscript_url, force=force)

    return {"ok": True, "results": all_results}


# ── /api/health ──────────────────────────────────────────────────────────

@app.get("/api/tmp/{filename}")
def serve_tmp_file(filename: str):
    """Serve a temporary file for Bambu HTTP pull upload."""
    from fastapi.responses import FileResponse
    path = Path("data/tmp") / filename
    if not path.exists():
        raise HTTPException(404, "Temp file not found")
    return FileResponse(str(path), media_type="application/octet-stream")


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
