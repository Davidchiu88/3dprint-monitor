"""
Printer Profiles — stores user-editable info per printer
(location, display name, task assignments, notes).
Stored in data/printer_profiles.json.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

PROFILES_FILE = Path("data/printer_profiles.json")

_DEFAULT_PROFILE = {
    "display_name": "",
    "location":     "",
    "tasks":        [],   # list of task strings e.g. ["精細模型", "快速打印"]
    "notes":        "",
    "color":        "",   # optional override color
    "enabled":      True,
}


class PrinterProfileStore:
    def __init__(self, path: Path = PROFILES_FILE):
        self.path = path
        self._data: Dict[str, Dict] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Failed to load profiles: {e}")

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"Failed to save profiles: {e}")

    def get(self, name: str) -> Dict:
        p = dict(_DEFAULT_PROFILE)
        p.update(self._data.get(name, {}))
        if not p["display_name"]:
            p["display_name"] = name
        return p

    def update(self, name: str, fields: Dict) -> Dict:
        allowed = {"display_name", "location", "tasks", "notes", "color", "enabled"}
        current = self.get(name)
        for k, v in fields.items():
            if k in allowed:
                current[k] = v
        self._data[name] = current
        self._save()
        return current

    def all_profiles(self) -> Dict[str, Dict]:
        return {name: self.get(name) for name in self._data}
