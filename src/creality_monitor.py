"""
Creality K1C Monitor - Polling WebSocket (port 9999)
K1C's built-in WS server doesn't support persistent connections,
so we connect → receive full state → disconnect → wait → repeat.
"""

import asyncio
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

import websockets

from .printer_base import PrinterMonitor, PrinterStatus

logger = logging.getLogger(__name__)

_STATE_MAP = {0: "IDLE", 1: "PRINTING", 2: "PAUSED", 4: "IDLE"}


def _parse_filename(path: str) -> str:
    name = path.split("/")[-1].split("\\")[-1]
    for ext in (".gcode", ".bgcode", ".3mf"):
        if name.lower().endswith(ext):
            name = name[: -len(ext)]
    return name


class CrealityK1CMonitor(PrinterMonitor):
    """Monitor for Creality K1C via polled WebSocket (port 9999)."""

    POLL_INTERVAL = 15   # seconds between polls

    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        status_callback: Optional[Callable[[PrinterStatus], None]] = None,
    ):
        super().__init__(name, config)
        self.ip = config.get("ip")
        self.ws_url = f"ws://{self.ip}:9999"
        self.status_callback = status_callback
        self._connected = False
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ── public interface ─────────────────────────────────────────────────

    def connect(self) -> bool:
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name=f"k1c-{self.name}"
        )
        self._thread.start()
        # wait up to 8 s for first successful poll
        for _ in range(80):
            if self.last_status:
                self._connected = True
                return True
            time.sleep(0.1)
        # still try: connection might be slow
        return False

    def disconnect(self) -> bool:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._connected = False
        return True

    def is_connected(self) -> bool:
        return self._connected

    def get_status(self) -> Optional[PrinterStatus]:
        return self.last_status

    # ── poll loop ────────────────────────────────────────────────────────

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._poll_loop())
        finally:
            loop.close()

    async def _poll_loop(self) -> None:
        while not self._stop.is_set():
            await self._do_poll()
            # Sleep POLL_INTERVAL but check stop every second
            for _ in range(self.POLL_INTERVAL):
                if self._stop.is_set():
                    return
                await asyncio.sleep(1)

    async def _do_poll(self) -> None:
        """Connect, collect 1-3 messages (full state + deltas), then disconnect."""
        state: Dict[str, Any] = {}
        try:
            async with websockets.connect(
                self.ws_url,
                ping_interval=None,
                open_timeout=5,
                close_timeout=3,
            ) as ws:
                self._connected = True
                # K1C sends a big full-state message first, then small deltas
                for _ in range(3):
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=4)
                        delta = json.loads(raw)
                        state.update(delta)
                    except asyncio.TimeoutError:
                        break
                    except Exception:
                        break

        except Exception as e:
            self._connected = False
            logger.debug(f"{self.name}: poll error: {e}")
            return

        self._connected = False

        if state:
            status = self._build_status(state)
            self.on_status_update(status)
            if self.status_callback:
                self.status_callback(status)

    def _build_status(self, s: Dict[str, Any]) -> PrinterStatus:
        nozzle        = float(s.get("nozzleTemp",       0) or 0)
        nozzle_target = float(s.get("targetNozzleTemp", 0) or 0)
        bed           = float(s.get("bedTemp0",         0) or 0)
        bed_target    = float(s.get("targetBedTemp0",   0) or 0)
        chamber       = float(s.get("boxTemp",          0) or 0)

        progress    = float(s.get("printProgress", 0) or 0)
        cur_layer   = int(s.get("layer",       0) or 0)
        total_layer = int(s.get("TotalLayer",  0) or 0)
        raw_state   = int(s.get("state",       0) or 0)
        state_str   = _STATE_MAP.get(raw_state, f"STATE_{raw_state}")

        raw_file  = s.get("printFileName", "") or ""
        print_file = _parse_filename(raw_file) if raw_file else None
        remaining  = int(s.get("printLeftTime", 0) or 0)

        err = s.get("err", {})
        error_msg = None
        if isinstance(err, dict) and err.get("errcode", 0):
            error_msg = f"errcode={err['errcode']}"

        return PrinterStatus(
            name=self.name,
            printer_type="creality_k1c",
            online=True,
            progress=progress,
            temp_nozzle=nozzle,
            temp_nozzle_target=nozzle_target,
            temp_bed=bed,
            temp_bed_target=bed_target,
            state=state_str,
            print_file=print_file,
            remaining_time=remaining,
            error=error_msg,
            extra_data={
                "layer":             f"{cur_layer}/{total_layer}" if total_layer else None,
                "chamber_temp":      chamber,
                "speed_pct":         s.get("curFeedratePct"),
                "real_speed_mm_s":   s.get("realTimeSpeed"),
                "model_fan_pct":     s.get("modelFanPct"),
                "hostname":          s.get("hostname"),
                "model":             s.get("model"),
                "used_material_mm":  s.get("usedMaterialLength"),
            },
        )
