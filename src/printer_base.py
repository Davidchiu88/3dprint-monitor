from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional


class PrinterStatus:
    """Standard status structure for all printers"""

    def __init__(
        self,
        name: str,
        printer_type: str,
        online: bool,
        progress: Optional[float] = None,
        temp_nozzle: Optional[float] = None,
        temp_nozzle_target: Optional[float] = None,
        temp_bed: Optional[float] = None,
        temp_bed_target: Optional[float] = None,
        state: Optional[str] = None,
        materials: Optional[Dict[str, Any]] = None,
        print_file: Optional[str] = None,
        remaining_time: Optional[int] = None,
        error: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.printer_type = printer_type
        self.online = online
        self.progress = progress
        self.temp_nozzle = temp_nozzle
        self.temp_nozzle_target = temp_nozzle_target
        self.temp_bed = temp_bed
        self.temp_bed_target = temp_bed_target
        self.state = state
        self.materials = materials or {}
        self.print_file = print_file
        self.remaining_time = remaining_time
        self.error = error
        self.extra_data = extra_data or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "printer_type": self.printer_type,
            "online": self.online,
            "progress": self.progress,
            "temp_nozzle": self.temp_nozzle,
            "temp_nozzle_target": self.temp_nozzle_target,
            "temp_bed": self.temp_bed,
            "temp_bed_target": self.temp_bed_target,
            "state": self.state,
            "materials": self.materials,
            "print_file": self.print_file,
            "remaining_time": self.remaining_time,
            "error": self.error,
            "timestamp": self.timestamp,
            "extra_data": self.extra_data,
        }


class PrinterMonitor(ABC):
    """Abstract base class for printer monitors"""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.last_status: Optional[PrinterStatus] = None

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the printer. Return True if successful."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the printer."""
        pass

    @abstractmethod
    def get_status(self) -> Optional[PrinterStatus]:
        """Get current printer status. Return None if failed."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if printer is currently connected."""
        pass

    def on_status_update(self, status: PrinterStatus) -> None:
        """Called when status is updated. Can be overridden for callbacks."""
        self.last_status = status
