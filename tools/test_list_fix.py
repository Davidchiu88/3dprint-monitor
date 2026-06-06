#!/usr/bin/env python3
"""Test list_files path generation."""
import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from src.printer_control import BambuController

c = BambuController('192.168.0.30', 'XXXXXXXXXXXXXXX', 'XXXXXXXX')
files = c.list_files()
print(f"Total: {len(files)}")
errors = [f for f in files if f.get('_error')]
if errors:
    print(f"Errors: {errors[0]}")
else:
    for f in files[:5]:
        print(f"  name={f['name']!r}  path={f['path']!r}")
