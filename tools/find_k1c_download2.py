#!/usr/bin/env python3
"""Find K1C gcode download method."""
import requests, sys, re
sys.stdout.reconfigure(encoding='utf-8')

ip = '192.168.0.205'
fname = '3DBenchy.gcode'

# Strategy 1: Try GET on the upload URL (same path as POST /upload/)
print("=== Strategy 1: GET /upload/filename ===")
try:
    r = requests.get(f'http://{ip}/upload/{fname}', timeout=5)
    print(f"  Status: {r.status_code}")
    print(f"  Content-Type: {r.headers.get('content-type','?')}")
    print(f"  Content-Length: {r.headers.get('content-length','?')}")
    if r.status_code == 200:
        print(f"  First 50 bytes: {r.content[:50]}")
except Exception as e:
    print(f"  Error: {e}")

# Strategy 2: Try filesystem-style paths
print("\n=== Strategy 2: Filesystem paths ===")
for path in [
    f'/usr/data/printer_data/gcodes/{fname}',
    f'/printer_data/gcodes/{fname}',
    f'/gcodes/{fname}',
    f'/data/gcodes/{fname}',
    f'/sdcard/{fname}',
]:
    try:
        r = requests.get(f'http://{ip}{path}', timeout=3)
        print(f"  {r.status_code} {path}")
        if r.status_code == 200:
            print(f"    Content-Type: {r.headers.get('content-type','?')}")
            print(f"    Size: {r.headers.get('content-length','?')}")
    except Exception as e:
        print(f"  ERR {path}: {str(e)[:40]}")

# Strategy 3: Check if there's a Moonraker/Fluidd API
print("\n=== Strategy 3: Klipper/Moonraker API ===")
for port in [7125, 80, 5000]:
    for ep in [f'/server/files/gcodes/{fname}', '/api/files/local']:
        try:
            r = requests.get(f'http://{ip}:{port}{ep}', timeout=3)
            if r.status_code != 404:
                print(f"  Port {port} {ep}: {r.status_code} {r.text[:100]}")
        except: pass

# Strategy 4: Scan the web app JS for any download URL
print("\n=== Strategy 4: JS download patterns ===")
try:
    js = requests.get(f'http://{ip}/static/js/app.b05d1c1a.js', timeout=8).text
    patterns = [
        r'download[^"\'`]{0,5}["\`\'](\/[^"\'`]{3,40})["\`\']',
        r'["\`\'](\/[a-z_/]{3,30}download[^"\'`]{0,20})["\`\']',
        r'href.*download|download.*href',
        r'window\.location.*=.*gcode',
    ]
    for pat in patterns:
        hits = re.findall(pat, js, re.IGNORECASE)
        if hits:
            print(f"  Pattern '{pat[:30]}': {list(set(hits))[:3]}")
except Exception as e:
    print(f"  JS scan error: {e}")

print("\n=== Strategy 5: FTP port scan ===")
import socket
for port in [21, 990, 2121, 8821, 9090]:
    s = socket.socket()
    s.settimeout(1)
    r = s.connect_ex((ip, port))
    s.close()
    if r == 0:
        print(f"  Port {port}: OPEN")
