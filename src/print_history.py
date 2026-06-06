"""
Print History — detects state transitions and logs each print job.

Transition logic:
  IDLE / UNKNOWN  → PRINTING   : start new record
  PRINTING        → IDLE/FINISH : mark completed
  PRINTING        → ERROR       : mark failed
  PRINTING        → PAUSED      : (just update, keep record open)
  PRINTING        → IDLE (no change in file) : completed
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from .printer_base import PrinterStatus

logger = logging.getLogger(__name__)

HISTORY_FILE = Path("data/print_history.json")
MAX_RECORDS  = 500   # keep most recent N records


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class PrintRecord:
    __slots__ = (
        "id", "printer_name", "printer_type",
        "file_name", "start_time", "end_time",
        "duration_sec", "status",
        "progress_at_end", "filament_used_mm",
        "materials", "thumbnail_url", "extra",
    )

    def __init__(self, printer_name: str, printer_type: str, file_name: str):
        self.id              = str(uuid.uuid4())[:8]
        self.printer_name    = printer_name
        self.printer_type    = printer_type
        self.file_name       = file_name or "Unknown"
        self.start_time      = _now_iso()
        self.end_time: Optional[str] = None
        self.duration_sec: Optional[int] = None
        self.status          = "printing"          # printing / completed / failed / cancelled
        self.progress_at_end: Optional[float] = None
        self.filament_used_mm: Optional[int] = None
        self.materials: Dict = {}   # AMS / filament info at start of print
        self.thumbnail_url: Optional[str] = None
        self.extra: Dict = {}

    def finish(self, status: str, status_obj: PrinterStatus) -> None:
        self.end_time     = _now_iso()
        self.status       = status
        self.progress_at_end = status_obj.progress

        # Calculate duration
        try:
            start = datetime.fromisoformat(self.start_time)
            end   = datetime.fromisoformat(self.end_time)
            self.duration_sec = int((end - start).total_seconds())
        except Exception:
            pass

        # Filament used (K1C provides this)
        extra = status_obj.extra_data or {}
        if extra.get("used_material_mm"):
            self.filament_used_mm = int(extra["used_material_mm"])

    def to_dict(self) -> Dict:
        return {k: getattr(self, k) for k in self.__slots__}

    @classmethod
    def from_dict(cls, d: Dict) -> "PrintRecord":
        obj = cls.__new__(cls)
        for k in cls.__slots__:
            setattr(obj, k, d.get(k))
        return obj


class PrintHistoryStore:
    def __init__(self, history_file: Path = HISTORY_FILE):
        self.history_file = history_file
        self.records: list[PrintRecord] = []
        self._active: Dict[str, PrintRecord] = {}   # printer_name → current record
        self._prev_state: Dict[str, str] = {}        # printer_name → last state
        self._prev_file:  Dict[str, str] = {}        # printer_name → last file
        self._load()

    # ── persistence ──────────────────────────────────────────────────────

    def _load(self) -> None:
        if self.history_file.exists():
            try:
                raw = json.loads(self.history_file.read_text(encoding="utf-8"))
                self.records = [PrintRecord.from_dict(r) for r in raw]
                logger.info(f"Loaded {len(self.records)} print records")
            except Exception as e:
                logger.error(f"Failed to load history: {e}")

    def _save(self) -> None:
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            trimmed = self.records[-MAX_RECORDS:]
            self.history_file.write_text(
                json.dumps([r.to_dict() for r in trimmed], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    # ── state transition detector ─────────────────────────────────────────

    def update(self, status: PrinterStatus) -> None:
        """Call this every time a printer status update arrives."""
        name      = status.name
        new_state = (status.state or "").upper()
        new_file  = status.print_file or ""
        prev_state = self._prev_state.get(name, "")
        prev_file  = self._prev_file.get(name, "")

        # ── PRINTING started ──
        if new_state == "PRINTING" and prev_state != "PRINTING":
            self._start_record(status)

        # ── File changed while printing (new job) ──
        elif new_state == "PRINTING" and new_file and new_file != prev_file and prev_file:
            # Finish old record as cancelled, start new
            if name in self._active:
                self._active[name].finish("cancelled", status)
                self.records.append(self._active.pop(name))
            self._start_record(status)

        # ── PRINTING ended ──
        elif prev_state == "PRINTING" and new_state != "PRINTING":
            if name in self._active:
                if new_state in ("IDLE", "FINISH"):
                    end_status = "completed" if (status.progress or 0) >= 95 else "cancelled"
                elif new_state == "ERROR":
                    end_status = "failed"
                elif new_state == "OFFLINE":
                    end_status = "cancelled"
                else:
                    end_status = "cancelled"

                self._active[name].finish(end_status, status)
                self.records.append(self._active.pop(name))
                self._save()
                logger.info(f"Print record saved: {name} → {end_status}")

        self._prev_state[name] = new_state
        self._prev_file[name]  = new_file

    def _start_record(self, status: PrinterStatus) -> None:
        name = status.name
        rec  = PrintRecord(
            printer_name  = name,
            printer_type  = status.printer_type or "",
            file_name     = status.print_file or "",
        )
        # Thumbnail URL for K1C
        extra = status.extra_data or {}
        if status.printer_type == "creality_k1c" and status.print_file:
            from .creality_monitor import _parse_filename
            ip = extra.get("ip") or ""
            if ip:
                rec.thumbnail_url = f"http://{ip}/downloads/humbnail/{status.print_file}.png"

        # Capture current materials/AMS state
        rec.materials = dict(status.materials or {})

        self._active[name] = rec
        safe_name = rec.file_name.encode('ascii', 'replace').decode()
        logger.info(f"Print started: {name} - {safe_name}")

    # ── query ────────────────────────────────────────────────────────────

    def get_all(self, limit: int = 100) -> list:
        """Return most recent records, newest first, including active prints."""
        active = list(self._active.values())
        finished = self.records[-limit:]
        combined = [r.to_dict() for r in active] + [r.to_dict() for r in reversed(finished)]
        return combined[:limit]

    def get_stats(self) -> Dict:
        completed = [r for r in self.records if r.status == "completed"]
        failed    = [r for r in self.records if r.status == "failed"]
        total_sec = sum(r.duration_sec or 0 for r in completed)
        return {
            "total":     len(self.records),
            "completed": len(completed),
            "failed":    len(failed),
            "active":    len(self._active),
            "total_print_hours": round(total_sec / 3600, 1),
        }
