import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .printer_base import PrinterStatus


logger = logging.getLogger(__name__)


class DataStore:
    """Manages persistence of printer status data"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.status_file = self.data_dir / "printer_status.json"
        self.history_file = self.data_dir / "printer_history.jsonl"
        self.current_status: Dict[str, Dict[str, Any]] = {}

        self._load_current_status()

    def _load_current_status(self) -> None:
        """Load current status from file"""
        if self.status_file.exists():
            try:
                with open(self.status_file, "r") as f:
                    self.current_status = json.load(f)
                logger.info(f"Loaded status for {len(self.current_status)} printers")
            except Exception as e:
                logger.warning(f"Failed to load status file: {e}")
                self.current_status = {}

    def save_status(self, status: PrinterStatus) -> None:
        """Save printer status to current and history"""
        try:
            # Save to current status
            self.current_status[status.name] = status.to_dict()

            # Write current status
            with open(self.status_file, "w") as f:
                json.dump(self.current_status, f, indent=2, default=str)

            # Append to history
            with open(self.history_file, "a") as f:
                f.write(json.dumps(status.to_dict(), default=str) + "\n")

        except Exception as e:
            logger.error(f"Failed to save status for {status.name}: {e}")

    def get_status(self, printer_name: str) -> Optional[Dict[str, Any]]:
        """Get current status of a printer"""
        return self.current_status.get(printer_name)

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get current status of all printers"""
        return self.current_status.copy()

    def get_history(self, printer_name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical status data"""
        history = []
        try:
            if self.history_file.exists():
                with open(self.history_file, "r") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            record = json.loads(line)
                            if printer_name is None or record.get("name") == printer_name:
                                history.append(record)
                        except json.JSONDecodeError:
                            continue

            # Return last 'limit' entries
            return history[-limit:] if history else []

        except Exception as e:
            logger.error(f"Failed to read history: {e}")
            return []

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all printer statuses"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "printers": {},
            "totals": {
                "online": 0,
                "printing": 0,
                "idle": 0,
                "error": 0,
            },
        }

        for name, status in self.current_status.items():
            # Count online/offline
            if status.get("online"):
                summary["totals"]["online"] += 1

            # Count by state
            state = status.get("state", "UNKNOWN").upper()
            if state == "PRINTING":
                summary["totals"]["printing"] += 1
            elif state == "IDLE":
                summary["totals"]["idle"] += 1
            elif state == "ERROR":
                summary["totals"]["error"] += 1

            # Store printer summary
            summary["printers"][name] = {
                "online": status.get("online"),
                "state": status.get("state"),
                "progress": status.get("progress"),
                "temp_nozzle": status.get("temp_nozzle"),
                "temp_bed": status.get("temp_bed"),
            }

        return summary

    def format_status_text(self) -> str:
        """Format status as readable text"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"Status: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)

        for name, status in self.current_status.items():
            lines.append(f"\n[{name}]")
            lines.append(f"   Type: {status.get('printer_type')}")
            lines.append(f"   Online: {'YES' if status.get('online') else 'NO'}")

            if status.get("online"):
                state = status.get("state", "UNKNOWN")
                lines.append(f"   State: {state}")

                if status.get("progress") is not None:
                    progress = status.get("progress", 0)
                    lines.append(f"   Progress: {progress:.1f}%")

                if status.get("print_file"):
                    lines.append(f"   File: {status.get('print_file')}")

                if status.get("temp_nozzle") is not None:
                    tn = status.get("temp_nozzle", 0)
                    tn_target = status.get("temp_nozzle_target", 0)
                    lines.append(f"   Nozzle: {tn:.0f}C / {tn_target:.0f}C target")

                if status.get("temp_bed") is not None:
                    tb = status.get("temp_bed", 0)
                    tb_target = status.get("temp_bed_target", 0)
                    lines.append(f"   Bed: {tb:.0f}C / {tb_target:.0f}C target")

                if status.get("remaining_time"):
                    remaining = status.get("remaining_time", 0)
                    lines.append(f"   Remaining: {remaining}s ({remaining//60}m)")

            if status.get("error"):
                lines.append(f"   [ERROR] {status.get('error')}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
