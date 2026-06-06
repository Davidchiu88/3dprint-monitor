import json
import logging
import ssl
import threading
import time
from typing import Dict, Any, Optional, Callable
import paho.mqtt.client as mqtt

from .printer_base import PrinterMonitor, PrinterStatus


logger = logging.getLogger(__name__)


def _make_tls_context() -> ssl.SSLContext:
    """Create TLS context compatible with Bambu Lab China-version firmware."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
    ctx.set_ciphers("ALL:@SECLEVEL=0")
    return ctx


class BambuLabMonitor(PrinterMonitor):
    """Monitor for Bambu Lab printers via local MQTT (paho-mqtt 2.x)."""

    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        status_callback: Optional[Callable[[PrinterStatus], None]] = None,
    ):
        super().__init__(name, config)
        self.ip = config.get("ip")
        self.device_id = config.get("device_id")
        self.access_code = config.get("access_code")
        self.status_callback = status_callback
        self.client: Optional[mqtt.Client] = None
        self._connected = False
        self._stop_event = threading.Event()
        self._state: Dict[str, Any] = {}  # merged state cache (delta updates merged here)

    # ── public interface ─────────────────────────────────────────────────

    def connect(self) -> bool:
        if self._connected:
            return True
        try:
            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.name,
            )
            self.client.on_connect    = self._on_connect
            self.client.on_message    = self._on_message
            self.client.on_disconnect = self._on_disconnect

            self.client.tls_set_context(_make_tls_context())
            self.client.username_pw_set("bblp", self.access_code)
            # Configure paho's built-in reconnect backoff (5s–60s)
            self.client.reconnect_delay_set(min_delay=5, max_delay=60)

            logger.info(f"Connecting to {self.name} at {self.ip}:8883...")
            self.client.connect(self.ip, 8883, keepalive=60)
            self.client.loop_start()
            self._stop_event.clear()

            for _ in range(100):          # wait up to 10 s
                if self._connected:
                    logger.info(f"Connected to {self.name}")
                    return True
                time.sleep(0.1)

            logger.warning(f"Timeout connecting to {self.name}")
            self.disconnect()
            return False

        except Exception as e:
            logger.error(f"Error connecting to {self.name}: {e}")
            self.disconnect()
            return False

    def disconnect(self) -> bool:
        self._stop_event.set()
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception as e:
                logger.debug(f"{self.name} disconnect: {e}")
        self._connected = False
        return True

    def is_connected(self) -> bool:
        return self._connected

    def get_status(self) -> Optional[PrinterStatus]:
        return self.last_status

    # ── MQTT callbacks ───────────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0 or str(reason_code) == "Success":
            logger.info(f"{self.name}: MQTT connected")
            self._connected = True
            topic = f"device/{self.device_id}/report"
            logger.info(f"{self.name}: subscribing to {topic}")
            client.subscribe(topic, qos=1)
            # Request full state dump
            self._send_pushall(client)
        else:
            logger.warning(f"{self.name}: MQTT connection refused: {reason_code}")
            self._connected = False

    def _send_pushall(self, client=None):
        """Ask printer to broadcast its full current state.
        Try both formats - A1/A1-Mini uses 'pushing', older models use 'print'.
        """
        import threading
        c = client or self.client
        if not c:
            return

        def _do():
            for payload in [
                json.dumps({"pushing": {"sequence_id": "0", "command": "pushall"}}),
                json.dumps({"print":   {"sequence_id": "1", "command": "push_status"}}),
            ]:
                try:
                    c.publish(f"device/{self.device_id}/request", payload, qos=1)
                except Exception:
                    pass
                import time as _t; _t.sleep(0.5)

        threading.Thread(target=_do, daemon=True).start()

    def _on_disconnect(self, client, userdata, flags, reason_code=None, properties=None):
        self._connected = False
        self._state.clear()   # Clear stale state on disconnect
        if reason_code and str(reason_code) != "Normal disconnection":
            logger.warning(f"{self.name}: disconnected: {reason_code}")
            # paho-mqtt 2.x loop_start() handles reconnect automatically
            # reconnect_delay_set is configured in connect() — no manual reconnect needed

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            # Merge delta into state cache, then build status
            p = payload.get("print", payload.get("pushing"))
            if p and isinstance(p, dict):
                # Only merge non-empty values so deltas don't erase full state
                for k, v in p.items():
                    if v is not None and v != "":
                        self._state[k] = v
            status = self._parse_status()
            if status:
                self.on_status_update(status)
                if self.status_callback:
                    self.status_callback(status)
        except json.JSONDecodeError:
            logger.debug(f"{self.name}: non-JSON message")
        except Exception as e:
            logger.error(f"{self.name}: message error: {e}")

    # ── status parsing ───────────────────────────────────────────────────

    def _parse_status(self) -> Optional[PrinterStatus]:
        """Build status from merged state cache."""
        try:
            p = self._state
            if not p:
                return None

            gcode_state   = p.get("gcode_state") or ""
            progress      = p.get("mc_percent", 0) or 0
            nozzle        = p.get("nozzle_temper")
            nozzle_target = p.get("nozzle_target_temper")
            bed           = p.get("bed_temper")
            bed_target    = p.get("bed_target_temper")

            # AMS materials
            materials = {}
            for ams in (p.get("ams", {}) or {}).get("ams", []):
                for tray in (ams.get("tray") or []):
                    tid    = tray.get("tray_id", "?")
                    ams_id = ams.get("id", "?")
                    color  = tray.get("tray_color", "666666") or "666666"
                    materials[f"AMS{ams_id}-{tid}"] = {
                        "type":   tray.get("tray_type") or tray.get("tray_sub_brands") or "?",
                        "color":  f"#{color[:6]}",
                        "remain": tray.get("remain", 0),
                    }

            layer       = p.get("layer_num")
            total_layer = p.get("total_layer_num")
            print_file  = p.get("gcode_file") or p.get("subtask_name")
            remaining   = p.get("mc_remaining_time")

            return PrinterStatus(
                name=self.name,
                printer_type="bambu_lab",
                online=True,
                progress=progress,
                temp_nozzle=nozzle,
                temp_nozzle_target=nozzle_target,
                temp_bed=bed,
                temp_bed_target=bed_target,
                state=self._normalize_state(gcode_state),
                materials=materials,
                print_file=print_file,
                remaining_time=remaining,
                extra_data={
                    "layer": f"{layer}/{total_layer}" if layer and total_layer else str(layer or ""),
                    "chamber_temp": p.get("chamber_temper"),
                },
            )
        except Exception as e:
            logger.error(f"{self.name}: parse error: {e}")
            return None

    @staticmethod
    def _normalize_state(s: str) -> str:
        return {"PRINTING": "PRINTING", "RUNNING": "PRINTING", "PAUSED": "PAUSED",
                "IDLE": "IDLE", "FAILED": "ERROR", "FINISH": "IDLE",
                "PREPARE": "PRINTING"}.get(s.upper(), s.upper())
