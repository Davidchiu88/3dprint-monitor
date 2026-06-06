#!/usr/bin/env python3
"""Diagnose A1 #2 MQTT connection."""
import ssl, paho.mqtt.client as mqtt, time, sys
sys.stdout.reconfigure(encoding='utf-8')

ip   = '192.168.0.70'
code = 'XXXXXXXX'
did  = 'XXXXXXXXXXXXXXX'

log = []

def on_connect(c, u, f, rc, props=None):
    log.append(f'on_connect: rc={rc}')
    if str(rc) == 'Success' or rc == 0:
        topic = f'device/{did}/report'
        c.subscribe(topic, 1)
        log.append(f'subscribed: {topic}')

def on_disconnect(c, u, f, rc=None, props=None):
    log.append(f'on_disconnect: rc={rc}')

def on_message(c, u, m):
    log.append(f'message on {m.topic}: {m.payload[:80]}')

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
ctx.set_ciphers('ALL:@SECLEVEL=0')

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='test_a1_2')
c.on_connect    = on_connect
c.on_disconnect = on_disconnect
c.on_message    = on_message
c.tls_set_context(ctx)
c.username_pw_set('bblp', code)

print(f"Connecting to {ip}:8883...")
c.connect(ip, 8883, keepalive=15)
c.loop_start()
time.sleep(10)
c.loop_stop()

print("Log:")
for l in log:
    print(f"  {l}")

if not log:
    print("  (no events)")
