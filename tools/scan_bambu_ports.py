#!/usr/bin/env python3
"""Full port scan on Bambu A1 Mini to find file management endpoints."""
import socket, ssl, requests, sys, concurrent.futures
sys.stdout.reconfigure(encoding='utf-8')

IP   = '192.168.0.30'
CODE = 'XXXXXXXX'

# ── Port scan ─────────────────────────────────────────────────────────
print("=== Scanning all common ports ===")
open_ports = []
def check_port(port):
    s = socket.socket()
    s.settimeout(0.5)
    r = s.connect_ex((IP, port))
    s.close()
    return port if r == 0 else None

with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
    ports_to_scan = list(range(1, 1024)) + [1883, 1884, 2121, 4840, 4843, 5000,
                                              8000, 8080, 8081, 8443, 8883, 8888, 9999,
                                              10000, 18883, 19000, 49000, 51413]
    results = list(ex.map(check_port, ports_to_scan))

open_ports = [p for p in results if p]
print(f"Open ports: {open_ports}")

# ── Try HTTP on open ports ─────────────────────────────────────────────
print("\n=== Testing HTTP on open ports ===")
for port in open_ports:
    for scheme in ['http', 'https']:
        try:
            url = f"{scheme}://{IP}:{port}/"
            r = requests.get(url, timeout=2, verify=False)
            print(f"  {url}: {r.status_code} - {r.text[:60].replace(chr(10),' ')}")
        except Exception as e:
            if 'CERTIFICATE_VERIFY_FAILED' not in str(e) and 'Connection refused' not in str(e):
                pass

# ── Try MQTT file commands ─────────────────────────────────────────────
print("\n=== Testing Bambu MQTT file list via push command ===")
import json, threading, time
import paho.mqtt.client as mqtt

msgs = []
def on_conn(c, u, f, rc, props=None):
    if rc == 0:
        c.subscribe(f'device/XXXXXXXXXXXXXXX/report', 1)
        # Try to get file list via different methods
        for payload in [
            '{"pushing":{"command":"pushall"}}',
            '{"print":{"command":"get_filelist"}}',
            '{"info":{"command":"get_version"}}',
        ]:
            c.publish(f'device/XXXXXXXXXXXXXXX/request', payload, 1)
            time.sleep(0.3)

def on_msg(c, u, m):
    try:
        d = json.loads(m.payload)
        # Look for file-related keys
        for k in d:
            if any(x in k.lower() for x in ['file', 'sdcard', 'storage', 'gcode']):
                msgs.append({k: d[k]})
                print(f"  Found: {k} = {str(d[k])[:100]}")
    except: pass

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT; ctx.set_ciphers("ALL:@SECLEVEL=0")

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='file_scan')
c.on_connect = on_conn; c.on_message = on_msg
c.tls_set_context(ctx); c.username_pw_set('bblp', CODE)
c.connect(IP, 8883, 30)
c.loop_start(); time.sleep(8); c.loop_stop()

if not msgs:
    print("  No file-related MQTT keys found")
