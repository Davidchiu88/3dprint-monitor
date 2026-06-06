#!/usr/bin/env python3
"""Extract K1C WebSocket command formats from JS source."""
import sys, re, requests, json
sys.stdout.reconfigure(encoding='utf-8')

ip = '192.168.0.205'
js = requests.get(f"http://{ip}/static/js/app.b05d1c1a.js", timeout=8).text

# Find all JSON-like objects sent to WebSocket
# Look for patterns like: ws.send(JSON.stringify({...})) or similar
print("=== WebSocket send patterns ===")
# Find sendMsg, send( patterns
contexts = []
for m in re.finditer(r'(?:send|emit|sendMsg)\s*\(\s*(?:JSON\.stringify\s*\()?\s*\{[^}]{10,200}\}', js):
    contexts.append(m.group()[:200])
for c in contexts[:10]:
    print(c)

print("\n=== startPrint context ===")
idx = js.find('startPrint')
if idx >= 0:
    print(js[max(0,idx-200):idx+300])

print("\n=== Upload/FormData context ===")
idx = js.find('FormData')
if idx >= 0:
    print(js[max(0,idx-200):idx+400])

print("\n=== File upload URL ===")
# Look for upload endpoint strings
for m in re.finditer(r'["\`\'](https?://[^"\']{5,80}|/[a-z][a-z_/]{3,40})["\`\']', js):
    v = m.group(1)
    if any(x in v.lower() for x in ['upload', 'file', 'gcode', 'print']):
        print(v)
