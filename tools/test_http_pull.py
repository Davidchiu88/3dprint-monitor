#!/usr/bin/env python3
"""Test Bambu HTTP Pull upload."""
import sys, requests, time
sys.stdout.reconfigure(encoding='utf-8')

API = 'http://localhost:7000'
data = b'; HTTP Pull test\nG28\nG1 X50 Y50 Z5\n'

print("=== Testing Bambu A1 Mini HTTP Pull upload ===")
r = requests.post(
    f'{API}/api/files/Bambu%20A1%20Mini',
    files={'file': ('http_pull_test.gcode', data)},
    timeout=20
)
d = r.json()
print(f"Response: ok={d.get('ok')}, method={d.get('method')}, file={d.get('filename')}")
if d.get('ok'):
    print("SUCCESS! Bambu printer should be downloading the file via HTTP...")
    # Check if tmp file exists
    r2 = requests.get(f'{API}/api/tmp/http_pull_test.gcode', timeout=3)
    print(f"Tmp file accessible: {r2.status_code == 200} ({len(r2.content)} bytes)")
else:
    print(f"FAILED: {d}")
