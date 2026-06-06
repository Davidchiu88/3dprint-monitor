#!/usr/bin/env python3
"""Debug K1C upload state check."""
import sys, asyncio, websockets, json
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

print(f"Python {sys.version}")

async def _state_check():
    async with websockets.connect('ws://192.168.0.205:9999', ping_interval=None, open_timeout=5) as ws:
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        d = json.loads(raw)
        state    = int(d.get("state", -1))
        progress = float(d.get("printProgress", 0) or 0)
        return state, progress

# Test _run approach
print("Testing asyncio.new_event_loop()._run approach...")
try:
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(_state_check())
    loop.close()
    print(f"OK! state={result[0]}, progress={result[1]}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

# Test asyncio.run approach (Python 3.7+)
print("\nTesting asyncio.run() approach...")
try:
    result = asyncio.run(_state_check())
    print(f"OK! state={result[0]}, progress={result[1]}")
except RuntimeError as e:
    print(f"RuntimeError: {e}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
