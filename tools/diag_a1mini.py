#!/usr/bin/env python3
"""Capture 5 real MQTT messages from A1 Mini and show all fields."""
import ssl, json, sys, time
import paho.mqtt.client as mqtt

sys.stdout.reconfigure(encoding='utf-8')

msgs = []

def on_conn(c, u, f, rc, props=None):
    if rc == 0:
        print("Connected!")
        c.subscribe("device/XXXXXXXXXXXXXXX/report", 1)
        time.sleep(0.3)
        c.publish("device/XXXXXXXXXXXXXXX/request",
                  '{"pushing":{"sequence_id":"0","command":"pushall"}}', 1)

def on_msg(c, u, m):
    try:
        d = json.loads(m.payload.decode("utf-8"))
        msgs.append(d)
        p = d.get("print", d.get("pushing", {}))
        if p and isinstance(p, dict):
            # Show any field that looks temperature or state related
            for k, v in p.items():
                if any(x in k.lower() for x in ["temp","state","status","percent","gcode","nozzle","bed","remain","file","layer"]):
                    print(f"  {k}: {v}")
            print("  ---")
    except Exception as e:
        print(f"  parse error: {e}")

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="diag_a1mini")
c.on_connect = on_conn
c.on_message = on_msg

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
ctx.set_ciphers("ALL:@SECLEVEL=0")
c.tls_set_context(ctx)
c.username_pw_set("bblp", "XXXXXXXX")

print("Connecting to A1 Mini (192.168.0.30)...")
c.connect("192.168.0.30", 8883, 30)
c.loop_start()
time.sleep(10)
c.loop_stop()
print(f"\nTotal messages received: {len(msgs)}")
