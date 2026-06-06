#!/usr/bin/env python3
"""Scan K1C JS for file upload / print control API patterns."""
import sys, re, requests
sys.stdout.reconfigure(encoding='utf-8')

ip = '192.168.0.205'
print(f"Fetching JS from {ip}...")
js = requests.get(f"http://{ip}/static/js/app.b05d1c1a.js", timeout=8).text
print(f"JS size: {len(js)}")

patterns = {
    "FormData / upload":  r'FormData|multipart|uploadFile|fileUpload',
    "Print commands":     r'startPrint|stopPrint|pausePrint|resumePrint|cancelPrint',
    "HTTP POST paths":    r'"(POST|PUT)",\s*["\']([^"\']{5,50})["\']',
    "Action field":       r'"action"\s*:\s*"([^"]{3,30})"',
    "Type field":         r'"type"\s*:\s*"([^"]{3,30})"',
    "WS commands":        r'"command"\s*:\s*"([^"]{3,30})"',
    "File paths in WS":   r'gcode[s]?|gcodes|printer_data',
}

for label, pat in patterns.items():
    hits = list(set(re.findall(pat, js, re.IGNORECASE)))[:6]
    if hits:
        print(f"\n{label}:")
        for h in hits:
            print(f"  {h}")

# Look for the pause/stop button handlers
print("\n\nContext around 'pause':")
idx = js.find('"pause"')
if idx > 0:
    print(js[max(0,idx-100):idx+100])

print("\nContext around 'stop':")
idx = js.find('"stop"')
if idx > 0:
    print(js[max(0,idx-100):idx+100])
