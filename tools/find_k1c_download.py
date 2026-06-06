#!/usr/bin/env python3
"""Find K1C gcode download URL."""
import requests, sys
sys.stdout.reconfigure(encoding='utf-8')

ip = '192.168.0.205'
fname = '3DBenchy.gcode'

# K1C JS source might have download URL
import re, requests as req
js = req.get(f'http://{ip}/static/js/app.b05d1c1a.js', timeout=8).text

# Search for download-related patterns
print("=== Download patterns in JS ===")
for pat in [r'"/(down[^"]{0,30})"', r'download[^"]{0,20}url', r'fileUrl', r'/file/']:
    hits = re.findall(pat, js, re.IGNORECASE)
    if hits:
        print(f"  Pattern '{pat}': {list(set(hits))[:3]}")

# Test paths
print("\n=== Testing paths ===")
for path in [
    f'/downloads/original/{fname}',
    f'/file/{fname}',
    f'/gcode/{fname}',
    f'/downloads/{fname}',
    f'/upload/{fname}',
    '/downloads/original/',
]:
    try:
        r = requests.head(f'http://{ip}{path}', timeout=3)
        cl = r.headers.get('Content-Length', '?')
        print(f"  {r.status_code} {path}  size={cl}")
    except Exception as e:
        print(f"  ERR {path}: {str(e)[:40]}")
