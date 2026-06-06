#!/usr/bin/env python3
"""Find K1C file transfer alternatives."""
import socket, sys, asyncio, json, websockets
sys.stdout.reconfigure(encoding='utf-8')

ip = '192.168.0.205'

# 1. Port scan for SSH/Samba/other
print("=== Port scan ===")
interesting_ports = {
    22: 'SSH',
    23: 'Telnet',
    445: 'Samba/SMB',
    139: 'NetBIOS',
    2049: 'NFS',
    5900: 'VNC',
    8080: 'HTTP alt',
    9090: 'HTTP alt',
    10000: 'HTTP alt',
    4840: 'OPC-UA',
    1935: 'RTMP',
    4022: 'SSH alt',
    8888: 'HTTP alt',
}
for port, name in interesting_ports.items():
    s = socket.socket()
    s.settimeout(0.8)
    r = s.connect_ex((ip, port))
    s.close()
    if r == 0:
        print(f"  Port {port} ({name}): OPEN")

# 2. Try WebSocket download command
print("\n=== WebSocket file read command ===")
async def try_ws_download():
    fname = '3DBenchy.gcode'
    folder = '/usr/data/printer_data/gcodes'

    cmds = [
        {"method": "get", "params": {"reqFileContent": 1, "path": f"{folder}/{fname}"}},
        {"method": "get", "params": {"readFile": f"{folder}/{fname}"}},
        {"method": "get", "params": {"downloadFile": f"{folder}/{fname}"}},
        {"method": "get", "params": {"reqGcodeContent": 1, "file": fname}},
    ]

    async with websockets.connect(f'ws://{ip}:9999', ping_interval=None, open_timeout=5) as ws:
        for cmd in cmds:
            await ws.send(json.dumps(cmd))
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=2)
                d = json.loads(raw)
                # Look for any non-standard keys
                interesting = {k: v for k, v in d.items()
                               if k not in ('nozzleTemp','bedTemp0','bedTemp1','bedTemp2',
                                            'curPosition','err','realTimeFlow','realTimeSpeed',
                                            'printFileName','printProgress','state','fan')}
                if interesting:
                    print(f"  Cmd: {list(cmd['params'].keys())[0]}")
                    print(f"  Response: {interesting}")
            except asyncio.TimeoutError:
                pass

asyncio.run(try_ws_download())

# 3. Try HTTP with Authorization header
print("\n=== HTTP with auth header ===")
import requests
for path in [f'/file/3DBenchy.gcode', f'/files/3DBenchy.gcode', '/api/files']:
    try:
        r = requests.get(f'http://{ip}{path}',
                        headers={'Authorization': 'Bearer bblp'},
                        timeout=3)
        if r.status_code != 404:
            print(f"  {r.status_code} {path}: {r.text[:80]}")
        else:
            print(f"  404 {path}")
    except Exception as e:
        print(f"  ERR {path}: {str(e)[:40]}")

# 4. Try accessing through port 8080 (MJPG server might serve more)
print("\n=== Port 8080 alternative paths ===")
for path in [f'/gcode/{fname}', '/', '/files']:
    try:
        r = requests.get(f'http://{ip}:8080{path}', timeout=3)
        print(f"  8080{path}: {r.status_code} {r.headers.get('content-type','?')}")
    except Exception as e:
        print(f"  ERR 8080{path}: {str(e)[:40]}")
