#!/usr/bin/env python3
"""Test multiple K1C rename command formats to find the correct one."""
import asyncio, json, sys, websockets, re, requests
sys.stdout.reconfigure(encoding='utf-8')

IP = '192.168.0.205'
# Use a safe test file (Benchy is a small test file)
TEST_FILE = "3DBenchy.gcode"
FOLDER    = "/usr/data/printer_data/gcodes"

async def send_and_check(msg: dict, label: str):
    """Send command and capture opGcodeFile-related response."""
    async with websockets.connect(f"ws://{IP}:9999", ping_interval=None, open_timeout=5) as ws:
        await ws.send(json.dumps(msg))
        print(f"\n[{label}] Sent: {msg['params']['opGcodeFile']}")
        for _ in range(8):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(raw)
                # Look for relevant fields
                for k in ('err','opGcodeFile','retOpGcodeFile','errcode','state'):
                    if k in data:
                        print(f"  {k}: {data[k]}")
            except asyncio.TimeoutError:
                pass

async def check_file_exists_http(name: str) -> bool:
    """Check if file thumbnail exists (fast)."""
    try:
        r = requests.head(f"http://{IP}/downloads/humbnail/{name[:-6]}.png", timeout=2)
        return r.status_code == 200
    except:
        return False

async def main():
    print(f"K1C Rename Test on {IP}")
    print(f"Test file: {TEST_FILE}\n")

    # Check file exists first
    exists = await check_file_exists_http(TEST_FILE)
    print(f"Benchy exists: {exists}")
    if not exists:
        print("File not found, trying with 3DBenchy...")
        TEST_FILE2 = "3DBenchy.gcode"
        # List a file that exists
        html = requests.get(f"http://{IP}/downloads/humbnail/", timeout=5).text
        thumbs = re.findall(r'href="([^"./][^"]*\.png)"', html)
        if thumbs:
            fname = thumbs[0][:-4] + ".gcode"
            print(f"Using: {fname}")
        else:
            print("No files found")
            return
    else:
        fname = TEST_FILE

    new_name = fname.replace('.gcode', '_test.gcode')
    old_path = f"{FOLDER}/{fname}"
    new_path = f"{FOLDER}/{new_name}"

    print(f"\nTesting rename: {fname} → {new_name}")

    # Format 1: renameprt:OLD_FULL_PATH:NEW_NAME (just filename)
    await send_and_check({
        "method": "set",
        "params": {"opGcodeFile": f"renameprt:{old_path}:{new_name}"}
    }, "Format 1: full_path:new_name")
    await asyncio.sleep(1)

    # Check if it worked
    if await check_file_exists_http(new_name):
        print(f"\n✓ FORMAT 1 WORKS!")
        # Rename back
        await send_and_check({"method":"set","params":{"opGcodeFile":f"renameprt:{new_path}:{fname}"}}, "Rename back")
        return

    # Format 2: renameprt:FOLDER/OLD:FOLDER/NEW (both full paths)
    await send_and_check({
        "method": "set",
        "params": {"opGcodeFile": f"renameprt:{old_path}:{new_path}"}
    }, "Format 2: full_path:full_path")
    await asyncio.sleep(1)

    if await check_file_exists_http(new_name):
        print(f"\n✓ FORMAT 2 WORKS!")
        await send_and_check({"method":"set","params":{"opGcodeFile":f"renameprt:{new_path}:{old_path}"}}, "Rename back")
        return

    # Format 3: renameprt:OLD_NAME:NEW_NAME (just filenames, no path)
    await send_and_check({
        "method": "set",
        "params": {"opGcodeFile": f"renameprt:{fname}:{new_name}"}
    }, "Format 3: old_name:new_name")
    await asyncio.sleep(1)

    if await check_file_exists_http(new_name):
        print(f"\n✓ FORMAT 3 WORKS!")
        await send_and_check({"method":"set","params":{"opGcodeFile":f"renameprt:{new_name}:{fname}"}}, "Rename back")
        return

    # Format 4: maybe it's FOLDER:OLD:NEW
    await send_and_check({
        "method": "set",
        "params": {"opGcodeFile": f"renameprt:{FOLDER}:{fname}:{new_name}"}
    }, "Format 4: folder:old:new")
    await asyncio.sleep(1)

    if await check_file_exists_http(new_name):
        print(f"\n✓ FORMAT 4 WORKS!")
        return

    print("\n✗ All rename formats FAILED")
    print("\nPossible reasons:")
    print("  1. Rename not supported while printing/paused (state=2)")
    print("  2. Different command name needed")
    print("  3. Firmware version doesn't support rename")

asyncio.run(main())
