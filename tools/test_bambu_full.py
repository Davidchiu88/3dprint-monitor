#!/usr/bin/env python3
"""Test Bambu upload + print via API."""
import requests, sys, time
sys.stdout.reconfigure(encoding='utf-8')

API = 'http://localhost:7000'

# 1. Upload to A1 Mini
print("=== Testing Bambu A1 Mini upload ===")
data = b'; Test\nG28\nG1 X50 Y50 Z5\n'
r = requests.post(
    f'{API}/api/files/Bambu%20A1%20Mini',
    files={'file': ('test_upload.gcode', data)},
    timeout=20
)
d = r.json()
print(f"Upload: ok={d.get('ok')}, file={d.get('filename')}, size={d.get('size')}")

# 2. List files to confirm it's there
time.sleep(2)
r2 = requests.get(f'{API}/api/files/Bambu%20A1%20Mini', timeout=12)
d2 = r2.json()
files = [f for f in (d2.get('files') or []) if not f.get('_error')]
found = any('test_upload' in f.get('name','') for f in files)
print(f"File visible after upload: {'YES' if found else 'NO'} (total: {len(files)})")

# 3. Check A1 Mini status
r3 = requests.get(f'{API}/api/status', timeout=5)
d3 = r3.json()
a1mini = d3.get('printers',{}).get('Bambu A1 Mini',{})
print(f"A1 Mini status: {a1mini.get('state')} {a1mini.get('progress')}% N={a1mini.get('temp_nozzle')}C")
