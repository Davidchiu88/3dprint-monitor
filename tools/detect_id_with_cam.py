#!/usr/bin/env python3
"""Try to get device ID by triggering camera + watching MQTT."""
import sys, ssl, socket, struct, json, time, threading
import paho.mqtt.client as mqtt
sys.stdout.reconfigure(encoding='utf-8')

ip   = sys.argv[1] if len(sys.argv) > 1 else '192.168.0.70'
code = sys.argv[2] if len(sys.argv) > 2 else 'XXXXXXXX'

found_id = [None]

# Trigger camera (port 6000) in background to wake up the printer
def trigger_camera():
    def _auth(user, pw):
        pkt = bytearray(80)
        struct.pack_into('<I', pkt, 0, 0x40)
        struct.pack_into('<I', pkt, 4, 0x3000)
        u = user.encode()[:32]; pkt[16:16+len(u)] = u
        p = pw.encode()[:32];   pkt[48:48+len(p)] = p
        return bytes(pkt)
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        s = socket.socket(); s.settimeout(10)
        tls = ctx.wrap_socket(s, server_hostname=ip)
        tls.connect((ip, 6000))
        tls.send(_auth('bblp', code))
        print("  Camera connected!")
        time.sleep(3)
        tls.close()
    except Exception as e:
        print(f"  Camera: {e}")

# MQTT listener
def on_connect(c, u, f, rc, props=None):
    if str(rc) == 'Success' or rc == 0:
        print("MQTT connected, subscribing...")
        c.subscribe("device/+/report", 1)
        c.subscribe("device/+/request", 1)

def on_message(c, u, m):
    topic = m.topic
    if "/report" in topic or "/request" in topic:
        parts = topic.split("/")
        if len(parts) >= 2 and parts[1] not in ['+', '']:
            found_id[0] = parts[1]
            try:
                d = json.loads(m.payload)
                p = d.get('print', {})
                print(f"\nDevice ID: {parts[1]}")
                print(f"  State: {p.get('gcode_state','?')}, "
                      f"Nozzle: {p.get('nozzle_temper','?')}°C")
            except:
                print(f"Device ID: {parts[1]}")

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
ctx.set_ciphers("ALL:@SECLEVEL=0")

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="id_detect")
c.on_connect = on_connect; c.on_message = on_message
c.tls_set_context(ctx)
c.username_pw_set('bblp', code)
c.connect(ip, 8883, 30)
c.loop_start()

# Trigger camera after 2 seconds
threading.Timer(2.0, trigger_camera).start()

time.sleep(12)
c.loop_stop()

if found_id[0]:
    print(f"\nSERIAL NUMBER / DEVICE ID: {found_id[0]}")
else:
    print("\n找不到 Device ID，請從印表機螢幕查看：")
    print("  設定 → 關於 → 序號")
