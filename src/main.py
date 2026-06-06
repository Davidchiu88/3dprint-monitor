"""
Printer Monitoring System — loads config/printers.yaml and monitors all printers.
Status updates are written to data/printer_status.json via callback.
"""

import logging
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import yaml

from .bambu_monitor import BambuLabMonitor
from .creality_monitor import CrealityK1CMonitor
from .camera_sync import CameraScheduler
from .data_store import DataStore
from .print_history import PrintHistoryStore
from .printer_base import PrinterMonitor, PrinterStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("printer_monitor.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


class PrinterMonitoringSystem:
    def __init__(self, config_file: str = "config/printers.yaml"):
        self.config_file = Path(config_file)
        self.monitors: Dict[str, PrinterMonitor] = {}
        self.data_store = DataStore()
        self.history    = PrintHistoryStore()
        self.camera_scheduler: Optional[CameraScheduler] = None
        self._running = False

    # ── status callback ──────────────────────────────────────────────────

    def _on_status(self, status: PrinterStatus) -> None:
        """Called immediately when any printer pushes a status update."""
        self.data_store.save_status(status)
        self.history.update(status)
        logger.debug(f"{status.name}: {status.state} {status.progress:.1f}%")

    # ── config ───────────────────────────────────────────────────────────

    def load_config(self) -> Dict:
        if not self.config_file.exists():
            logger.error(f"Config not found: {self.config_file}")
            return {}
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    def initialize_monitors(self) -> None:
        config = self.load_config()
        printers = config.get("printers", [])
        logger.info(f"Initializing {len(printers)} printer(s)...")

        for pc in printers:
            name = pc.get("name")
            ptype = pc.get("type")
            if not name or not ptype:
                continue
            try:
                if ptype == "bambu_lab":
                    m = BambuLabMonitor(name, pc, status_callback=self._on_status)
                elif ptype == "creality_k1c":
                    m = CrealityK1CMonitor(name, pc, status_callback=self._on_status)
                else:
                    logger.warning(f"Unknown printer type: {ptype}")
                    continue
                self.monitors[name] = m
                logger.info(f"  Created: {name} ({ptype})")
            except Exception as e:
                logger.error(f"Failed to create monitor for {name}: {e}")

    def connect_all(self) -> None:
        logger.info("Connecting to all printers...")
        for name, monitor in self.monitors.items():
            try:
                ok = monitor.connect()
                icon = "✓" if ok else "✗"
                logger.info(f"  {icon} {name}")
            except Exception as e:
                logger.error(f"Error connecting {name}: {e}")

    def disconnect_all(self) -> None:
        for name, monitor in self.monitors.items():
            try:
                monitor.disconnect()
            except Exception as e:
                logger.debug(f"Disconnect error {name}: {e}")

    # ── lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> None:
        logger.info("=" * 50)
        logger.info("3D Printer Monitoring System starting...")
        logger.info("=" * 50)
        self._running = True

        try:
            self.initialize_monitors()
            self.connect_all()

            # Mark offline printers that couldn't connect
            config = self.load_config()
            for pc in config.get("printers", []):
                name = pc.get("name")
                if name and name not in self.monitors:
                    continue
                m = self.monitors.get(name)
                if m and not m.last_status:
                    from .printer_base import PrinterStatus
                    offline = PrinterStatus(
                        name=name,
                        printer_type=pc.get("type", "unknown"),
                        online=False,
                        state="OFFLINE",
                    )
                    self.data_store.save_status(offline)

            # ── Start camera scheduler (30 min snapshots) ──
            drive_cfg_file = Path("data/drive_config.json")
            gscript_url = ""
            if drive_cfg_file.exists():
                try:
                    import json as _json
                    gscript_url = _json.loads(drive_cfg_file.read_text(encoding="utf-8")).get("gscript_url","")
                except Exception:
                    pass
            self.camera_scheduler = CameraScheduler(
                printers_config=config.get("printers", []),
                gscript_url=gscript_url,
                snapshot_interval_min=30,
            )
            self.camera_scheduler.start()

            logger.info("All printers connected. Monitoring active.")
            logger.info("Camera scheduler: snapshots every 30 min → data/snapshots/")
            logger.info("API server should be running on port 7000.")
            logger.info("Press Ctrl+C to stop.\n")

            while self._running:
                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            self.stop()

    def stop(self) -> None:
        self._running = False
        if self.camera_scheduler:
            self.camera_scheduler.stop()
        self.disconnect_all()
        logger.info("Monitoring system stopped.")


def main():
    system = PrinterMonitoringSystem()

    def _sig(signum, frame):
        system.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _sig)

    system.start()


if __name__ == "__main__":
    main()
