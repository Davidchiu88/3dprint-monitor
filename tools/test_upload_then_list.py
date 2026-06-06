#!/usr/bin/env python3
"""Upload a file then check it appears in the list."""
import sys, requests, time
sys.stdout.reconfigure(encoding='utf-8')

API  = 'http://localhost:7000'
NAME = 'Creality K1C 紅'
ENC  = 'Creality%20K1C%20%E7%B4%85'

# Count files before
r = requests.get(f'{API}/api/files/{ENC}', timeout=10)
before = len([f for f in r.json().get('files', []) if not f.get('_error')])
print(f"Files before upload: {before}")

# Upload test file
test_gcode = b"; Uploaded by test\nG28\nG1 X50 Y50 Z5 F3000\n"
fname = f"_visibility_test.gcode"
r2 = requests.post(f'{API}/api/files/{ENC}',
                   files={'file': (fname, test_gcode)}, timeout=30)
d = r2.json()
print(f"Upload result: ok={d.get('ok')}, filename={d.get('filename')}")

if not d.get('ok'):
    print("Upload failed!")
    sys.exit(1)

print("Waiting 7 seconds for thumbnail generation...")
time.sleep(7)

# Check file appears
r3 = requests.get(f'{API}/api/files/{ENC}', timeout=10)
files = [f for f in r3.json().get('files', []) if not f.get('_error')]
after = len(files)
found = any(f.get('name','') == fname for f in files)

print(f"Files after upload: {after} (was {before})")
print(f"Test file visible: {'YES!' if found else 'NO - still not visible'}")

if found:
    f = next(f for f in files if f.get('name') == fname)
    print(f"  thumbnail: {'yes' if f.get('thumbnail') else 'no (still generating)'}")
    # Cleanup
    r4 = requests.delete(f'{API}/api/files/{ENC}', params={'file': f['path']}, timeout=10)
    print(f"  Cleaned up: {r4.json().get('ok')}")
