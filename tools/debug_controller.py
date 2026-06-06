#!/usr/bin/env python3
"""Debug _get_controller for K1C printers."""
import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

# Test exact same path as API
from src.api_server import _get_controller

# These are the URL-decoded names the API receives
test_names = [
    'Creality K1C 紅',
    'Creality K1C 黑',
    'Bambu A1 Mini',
]

for name in test_names:
    c = _get_controller(name)
    if c:
        print(f"✅ {name!r}: {type(c).__name__} ip={c.ip}")
    else:
        print(f"❌ {name!r}: None (not found)")

# Also show what's in the config
import yaml
cfg = yaml.safe_load(open('config/printers.yaml', encoding='utf-8'))
print("\n=== Config names ===")
for p in cfg.get('printers', []):
    print(f"  {p['name']!r}")

# And status file keys
import json
from pathlib import Path
status = json.loads(Path('data/printer_status.json').read_text(encoding='utf-8'))
print("\n=== Status keys ===")
for k in status:
    print(f"  {k!r}")
