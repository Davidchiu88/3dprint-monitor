#!/usr/bin/env python3
"""End-to-end test of K1C upload via API server (same path as web page)."""
import sys, os, requests, time
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

API = 'http://localhost:7000'

# Test 1: K1C 紅 (IDLE - should upload directly)
print("=== Test 1: K1C 紅 (IDLE) ===")
test_gcode = b"; Test upload\nG28\nG1 X10 Y10 Z5 F3000\n"
r = requests.post(
    f'{API}/api/files/Creality%20K1C%20%E7%B4%85',
    files={'file': ('e2e_test.gcode', test_gcode, 'application/octet-stream')},
    timeout=30
)
print(f"  Status: {r.status_code}")
d = r.json()
print(f"  Response: ok={d.get('ok')}, filename={d.get('filename')}, size={d.get('size')}")

if d.get('ok'):
    print("  Upload SUCCESS! Checking file appears in list...")
    time.sleep(2)
    r2 = requests.get(f'{API}/api/files/Creality%20K1C%20%E7%B4%85', timeout=10)
    files = r2.json().get('files', [])
    found = any(f.get('name','').startswith('e2e_test') for f in files)
    print(f"  File in list: {'YES' if found else 'NOT YET (thumbnail may take time)'}")

    # Cleanup via API
    if found:
        cleanup_path = next((f.get('path') for f in files if f.get('name','').startswith('e2e_test')), None)
        if cleanup_path:
            r3 = requests.delete(f'{API}/api/files/Creality%20K1C%20%E7%B4%85',
                                  params={'file': cleanup_path}, timeout=10)
            print(f"  Cleanup: {r3.json().get('ok')}")
else:
    print(f"  Upload FAILED: {d}")

# Test 2: K1C 黑 (PAUSED 100% - should auto-clear and upload)
print("\n=== Test 2: K1C 黑 (PAUSED 100% → auto-clear) ===")
r = requests.post(
    f'{API}/api/files/Creality%20K1C%20%E9%BB%91',
    files={'file': ('e2e_test2.gcode', test_gcode, 'application/octet-stream')},
    timeout=30
)
print(f"  Status: {r.status_code}")
d = r.json()
print(f"  Response: ok={d.get('ok')}, filename={d.get('filename')}")
if d.get('ok'):
    print("  Auto-clear + Upload SUCCESS!")
else:
    print(f"  Result: {d}")
