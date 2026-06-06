#!/usr/bin/env python3
"""Test K1C file rename via WebSocket."""
import asyncio, json, sys, time, websockets
sys.stdout.reconfigure(encoding='utf-8')

IP = '192.168.0.205'  # K1C Red

async def send_cmd(msg: dict, wait=2.0):
    """Send a command and collect responses for wait seconds."""
    responses = []
    async with websockets.connect(f"ws://{IP}:9999", ping_interval=None, open_timeout=5) as ws:
        await ws.send(json.dumps(msg))
        print(f"Sent: {json.dumps(msg)}")
        deadline = asyncio.get_event_loop().time() + wait
        while asyncio.get_event_loop().time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(raw)
                # Show non-temp fields
                interesting = {k: v for k, v in data.items()
                               if k not in ('nozzleTemp','bedTemp0','bedTemp1',
                                            'bedTemp2','curPosition','realTimeFlow',
                                            'realTimeSpeed')}
                if interesting:
                    print(f"  Response: {interesting}")
                    responses.append(data)
            except asyncio.TimeoutError:
                pass
    return responses

async def list_files():
    """Get file list."""
    files = []
    async with websockets.connect(f"ws://{IP}:9999", ping_interval=None, open_timeout=5) as ws:
        await ws.send(json.dumps({"method":"get","params":{"reqGcodeFile":1}}))
        for _ in range(20):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                data = json.loads(raw)
                info = data.get("retGcodeFileInfo")
                if info:
                    fi = info.get("fileInfo","")
                    if fi:
                        parts = fi.split(":")
                        if len(parts) >= 2:
                            files.append({"name": parts[1], "folder": parts[0]})
            except asyncio.TimeoutError:
                if files: break
    return files

async def main():
    print(f"Testing K1C rename on {IP}\n")

    # Step 1: List files to find a test file
    print("=== Step 1: List files ===")
    files = await list_files()
    if not files:
        print("No files found - using known file from status")
        # Use the file we know exists from previous testing
        test_file = {
            "name":   "3DBenchy.gcode",
            "folder": "/usr/data/printer_data/gcodes"
        }
    else:
        # Use a non-critical file for testing (pick Benchy if available)
        test_file = next((f for f in files if 'benchy' in f['name'].lower()
                          or 'Benchy' in f['name']), files[-1])
        print(f"Files found: {len(files)}")
        print(f"Using test file: {test_file['name']}")

    old_path = f"{test_file['folder']}/{test_file['name']}"
    new_name = test_file['name'].replace('.gcode', '_renamed.gcode')

    # Step 2: Try rename
    print(f"\n=== Step 2: Rename ===")
    print(f"Old: {old_path}")
    print(f"New name: {new_name}")
    cmd = {"method": "set", "params": {"opGcodeFile": f"renameprt:{old_path}:{new_name}"}}
    await send_cmd(cmd, wait=3.0)

    # Step 3: Check if rename worked
    print(f"\n=== Step 3: Verify ===")
    time.sleep(2)
    files_after = await list_files()
    found_old = any(f['name'] == test_file['name'] for f in files_after)
    found_new = any(f['name'] == new_name for f in files_after)
    print(f"Original name still exists: {found_old}")
    print(f"New name exists: {found_new}")

    if found_new and not found_old:
        print("\n✓ RENAME WORKED! Now renaming back...")
        # Rename back
        new_path = f"{test_file['folder']}/{new_name}"
        cmd_back = {"method": "set", "params": {"opGcodeFile": f"renameprt:{new_path}:{test_file['name']}"}}
        await send_cmd(cmd_back, wait=2.0)
        print("Renamed back to original.")
    elif found_old and not found_new:
        print("\n✗ RENAME FAILED - file still has old name")
    else:
        print("\n? Could not verify (file list may be incomplete)")
        # Show all files
        for f in files_after[:5]:
            print(f"  {f['name']}")

asyncio.run(main())
