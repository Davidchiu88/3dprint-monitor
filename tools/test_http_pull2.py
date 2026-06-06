#!/usr/bin/env python3
"""Test Bambu HTTP Pull - detailed debug."""
import sys, requests, time
sys.stdout.reconfigure(encoding='utf-8')

API = 'http://localhost:7000'

# 1. Check local IP detection
r = requests.get(f'{API}/api/health', timeout=5)
print(f"API health: {r.json()}")

# 2. Upload with longer wait
data = b'; HTTP Pull test\nG28\nG1 X50 Y50 Z5\n'
print("\nUploading to Bambu A1 Mini...")
t0 = time.time()
r = requests.post(
    f'{API}/api/files/Bambu%20A1%20Mini',
    files={'file': ('pull_test.gcode', data)},
    timeout=10
)
print(f"Response ({time.time()-t0:.1f}s): {r.json()}")

# 3. Check tmp file (wait for background task)
print("\nWaiting 5s for background task...")
time.sleep(5)
r2 = requests.get(f'{API}/api/tmp/pull_test.gcode', timeout=3)
print(f"Tmp file: status={r2.status_code}, size={len(r2.content)}B")

# 4. Check log for upload activity
import subprocess
try:
    out = subprocess.run(
        ['python', '-c', '''
import sys
sys.stdout.reconfigure(encoding="utf-8")
lines = open("printer_monitor.log", encoding="utf-8", errors="replace").readlines()
for l in lines[-30:]:
    if any(x in l for x in ["upload","http","pull","tmp","project","Background","ERROR","Bambu FTP"]):
        print(l.rstrip())
'''],
        capture_output=True, text=True, timeout=5, cwd='D:/3Dprint'
    )
    print("\nRelevant logs:")
    print(out.stdout or "(none)")
except: pass
