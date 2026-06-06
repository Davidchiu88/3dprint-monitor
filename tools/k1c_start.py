#!/usr/bin/env python3
import sys, re, requests
sys.stdout.reconfigure(encoding='utf-8')
ip = '192.168.0.205'
js = requests.get(f"http://{ip}/static/js/app.b05d1c1a.js", timeout=8).text

# Find operType 1 (startPrint) handler
print("=== operType 1 context ===")
for m in re.finditer(r'operType.{0,300}', js):
    txt = m.group()
    if 'startPrint' in txt or 'printFile' in txt or '1===e.operType' in txt:
        print(txt[:400])
        print("---")

print("\n=== sendMsg near startPrint ===")
idx = js.find('startPrint')
while idx >= 0:
    ctx = js[max(0,idx-300):idx+300]
    if 'sendMsg' in ctx or 'method' in ctx:
        print(ctx)
        print("---")
    idx = js.find('startPrint', idx+1)

print("\n=== printGcode / gcode_file patterns ===")
for m in re.finditer(r'(printGcode|gcode_file|startGcode|gcodeFile|printFile)[^;]{0,200}', js):
    print(m.group()[:200])
