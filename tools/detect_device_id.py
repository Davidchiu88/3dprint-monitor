#!/usr/bin/env python3
"""Detect Bambu Lab device_id by subscribing to device/+/report wildcard."""
import sys, ssl, json, time
import paho.mqtt.client as mqtt
sys.stdout.reconfigure(encoding='utf-8')

ip   = sys.argv[1] if len(sys.argv) > 1 else '192.168.0.70'
code = sys.argv[2] if len(sys.argv) > 2 else 'XXXXXXXX'

found_id = [None]

def on_connect(c, u, f, rc, props=None):
    if str(rc) == 'Success' or rc == 0:
        print(f"Connected! Subscribing to device/+/report...")
        c.subscribe("device/+/report", 1)
        # Also send pushall to any device (won't work without ID but might trigger response)
        c.subscribe("#", 1)  # subscribe all to catch any message
    else:
        print(f"Failed: {rc}")

def on_message(c, u, m):
    topic = m.topic
    # Topic format: device/{DEVICE_ID}/report
    if topic.startswith("device/") and "/report" in topic:
        parts = topic.split("/")
        if len(parts) >= 2:
            device_id = parts[1]
            if device_id and device_id != '+':
                found_id[0] = device_id
                print(f"\n  FOUND Device ID: {device_id}")
                try:
                    payload = json.loads(m.payload)
                    p = payload.get('print', {})
                    if p:
                        print(f"  State: {p.get('gcode_state','?')}")
                        print(f"  Progress: {p.get('mc_percent','?')}%")
                        print(f"  Nozzle: {p.get('nozzle_temper','?')}°C")
                except:
                    pass
    elif topic:
        # Show any other topics
        print(f"  Topic: {topic}")

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
ctx.set_ciphers("ALL:@SECLEVEL=0")

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="detect_id")
c.on_connect = on_message and on_connect
c.on_message = on_message
c.tls_set_context(ctx)
c.username_pw_set('bblp', code)

print(f"Connecting to {ip}:8883...")
c.connect(ip, 8883, 30)
c.loop_start()
time.sleep(10)
c.loop_stop()

if found_id[0]:
    print(f"\nDevice ID: {found_id[0]}")
    print(f"\nAdd to config/printers.yaml:")
    print(f'  - name: "Bambu A1 #2"')
    print(f'    type: "bambu_lab"')
    print(f'    ip: "{ip}"')
    print(f'    device_id: "{found_id[0]}"')
    print(f'    access_code: "{code}"')
else:
    print("\nCouldn't detect device ID automatically.")
    print("印表機可能在空閒狀態，請在印表機螢幕查看序號")
    print("或在 Bambu Handy App > 裝置 > 設定 > 序號")
