#!/usr/bin/env python3
"""
Auto-detect Bambu Lab Device ID from MQTT broker.
Subscribes to '#' wildcard to capture the device ID from topic names.

Usage:
  python tools/find_device_id.py 192.168.0.30 XXXXXXXX
  python tools/find_device_id.py 192.168.0.58 XXXXXXXX
"""

import json
import ssl
import sys
import time
import paho.mqtt.client as mqtt


def find_device_id(ip: str, access_code: str):
    print(f"\nConnecting to {ip}:8883 with access code {access_code}...")
    found_ids = set()

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("  Connected! Listening for device topics...")
            client.subscribe("#", qos=0)
        else:
            print(f"  Connection failed: {rc}")

    def on_message(client, userdata, msg):
        topic = msg.topic
        # Topics look like: device/{DEVICE_ID}/report
        if topic.startswith("device/") and "/" in topic[7:]:
            parts = topic.split("/")
            if len(parts) >= 2:
                device_id = parts[1]
                if device_id not in found_ids:
                    found_ids.add(device_id)
                    print(f"\n  FOUND Device ID: {device_id}")
                    try:
                        payload = json.loads(msg.payload)
                        # Try to extract printer type from payload
                        if "print" in payload:
                            state = payload["print"].get("gcode_state", "?")
                            print(f"  State: {state}")
                    except Exception:
                        pass

    client = mqtt.Client(client_id="finder")
    client.on_connect = on_connect
    client.on_message = on_message

    client.tls_set(cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1_2)
    client.tls_insecure_set(True)
    client.username_pw_set("bblp", access_code)

    try:
        client.connect(ip, 8883, keepalive=30)
        client.loop_start()

        print("  Waiting 8 seconds for data...")
        time.sleep(8)
        client.loop_stop()
        client.disconnect()

    except Exception as e:
        print(f"  Error: {e}")
        return None

    if found_ids:
        print(f"\n  Device IDs found: {', '.join(found_ids)}")
        return list(found_ids)[0]
    else:
        print("\n  No device ID found automatically.")
        print("  Try: Bambu Lab App > Device > Settings > Serial Number")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python tools/find_device_id.py <IP> <ACCESS_CODE>")
        sys.exit(1)

    ip = sys.argv[1]
    code = sys.argv[2]
    find_device_id(ip, code)
