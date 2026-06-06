#!/usr/bin/env python3
import sys, re, requests
sys.stdout.reconfigure(encoding='utf-8')
ip = '192.168.0.205'
js = requests.get(f"http://{ip}/static/js/app.b05d1c1a.js", timeout=8).text

# Find the _() function that runs for operType 1 (startPrint)
# The pattern is: 1===e.operType&&_()
# Let's find what _ is
idx = js.find('1===e.operType&&_()')
if idx >= 0:
    # Get surrounding context
    print("Found operType 1 handler context:")
    print(js[max(0,idx-500):idx+500])

# Also look for reqPrintObject or printFile WebSocket method
print("\n\n=== All sendMsg calls ===")
for m in re.finditer(r'sendMsg\s*\(\s*\{[^}]{5,150}\}', js):
    print(m.group())
