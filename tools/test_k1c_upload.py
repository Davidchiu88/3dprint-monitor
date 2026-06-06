#!/usr/bin/env python3
"""Test K1C file upload."""
import requests, sys
sys.stdout.reconfigure(encoding='utf-8')

ip = '192.168.0.205'

# Create a minimal valid gcode test file
test_gcode = b"""; Test file - safe to delete
G28 ; home
G1 X0 Y0 Z10 F3000
"""

print(f"Testing upload to K1C 紅 ({ip})...")
print(f"File size: {len(test_gcode)} bytes")

try:
    r = requests.post(
        f'http://{ip}/upload/test_upload_probe.gcode',
        files={'file': ('test_upload_probe.gcode', test_gcode)},
        timeout=15
    )
    print(f"HTTP Status: {r.status_code}")
    print(f"Response: {r.text[:200]}")

    if r.status_code == 200:
        try:
            d = r.json()
            print(f"code={d.get('code')}")
            if d.get('code') == 200:
                print("Upload SUCCESS!")
                # Clean up test file
                import asyncio, websockets, json
                async def delete():
                    async with websockets.connect(f'ws://{ip}:9999', ping_interval=None, open_timeout=5) as ws:
                        await ws.send(json.dumps({"method":"set","params":{"opGcodeFile":"deleteprt:/usr/data/printer_data/gcodes/test_upload_probe.gcode"}}))
                        await asyncio.sleep(1)
                asyncio.run(delete())
                print("Test file cleaned up")
            else:
                print(f"Upload returned code={d.get('code')}: might indicate failure")
        except:
            print(f"Non-JSON response")
except Exception as e:
    print(f"Upload failed: {type(e).__name__}: {e}")
