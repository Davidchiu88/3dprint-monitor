#!/usr/bin/env python3
"""Test upload via API with a safe filename."""
import sys, requests, time
sys.stdout.reconfigure(encoding='utf-8')

API = 'http://localhost:7000'
ENC = 'Creality%20K1C%20%E7%B4%85'

# Use a safe filename (no leading underscore)
test_gcode = b"; Test upload via API\nG28\n"
fname = "api_test_file.gcode"

print(f"Uploading '{fname}' via API...")
r = requests.post(
    f'{API}/api/files/{ENC}',
    files={'file': (fname, test_gcode, 'application/octet-stream')},
    timeout=30
)
print(f"Status: {r.status_code}")
d = r.json()
print(f"Response: ok={d.get('ok')}, filename={d.get('filename')}, size={d.get('size')}")

if d.get('ok'):
    print("Upload SUCCESS! Waiting 7s for thumbnail...")
    time.sleep(7)
    # Check it appears
    r2 = requests.get(f'{API}/api/files/{ENC}', timeout=10)
    files = r2.json().get('files', [])
    found = any(f.get('name','') == fname for f in files if not f.get('_error'))
    print(f"Visible in file list: {'YES' if found else 'NOT YET (thumbnail still generating)'}")
    # Cleanup
    if found:
        f = next(f for f in files if f.get('name') == fname)
        requests.delete(f'{API}/api/files/{ENC}', params={'file': f['path']}, timeout=10)
        print("Cleaned up test file")
else:
    print(f"FAILED: {d}")
