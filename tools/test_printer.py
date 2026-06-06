#!/usr/bin/env python3
"""
Test connection and status for a single printer
Usage:
  python tools/test_printer.py creality 192.168.1.100
  python tools/test_printer.py bambu 192.168.1.101 DEVICE_ID ACCESS_CODE
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.creality_monitor import CrealityK1CMonitor
from src.bambu_monitor import BambuLabMonitor


def test_creality(ip: str):
    print(f"\nTesting Creality K1C at {ip}...")
    config = {"ip": ip}
    monitor = CrealityK1CMonitor("Test K1C", config)

    print("  Connecting...")
    connected = monitor.connect()
    print(f"  Connected: {connected}")

    if connected:
        print("  Waiting for first data...")
        import time as _time
        for _ in range(30):
            if monitor.last_status:
                break
            _time.sleep(0.2)
        status = monitor.get_status()
        if status:
            print(f"\n  Status:")
            print(f"    State:    {status.state}")
            print(f"    Progress: {status.progress:.1f}%" if status.progress is not None else "    Progress: N/A")
            print(f"    Nozzle:   {status.temp_nozzle:.0f}°C / {status.temp_nozzle_target:.0f}°C" if status.temp_nozzle else "    Nozzle: N/A")
            print(f"    Bed:      {status.temp_bed:.0f}°C / {status.temp_bed_target:.0f}°C" if status.temp_bed else "    Bed: N/A")
            print(f"    File:     {status.print_file or 'None'}")
            print(f"\n  Full JSON:")
            d = status.to_dict()
            d.pop("extra_data", None)  # Remove raw data for clarity
            print("  " + json.dumps(d, indent=4, default=str).replace("\n", "\n  "))
        else:
            print("  Failed to get status")

    monitor.disconnect()


def test_bambu(ip: str, device_id: str, access_code: str):
    print(f"\nTesting Bambu Lab at {ip} (device: {device_id})...")
    config = {"ip": ip, "device_id": device_id, "access_code": access_code}

    last_status = [None]

    def on_status(status):
        last_status[0] = status
        print(f"\n  Got MQTT update:")
        print(f"    State:    {status.state}")
        print(f"    Progress: {status.progress:.1f}%" if status.progress is not None else "    Progress: N/A")
        print(f"    Nozzle:   {status.temp_nozzle:.0f}°C / {status.temp_nozzle_target:.0f}°C" if status.temp_nozzle else "    Nozzle: N/A")
        print(f"    Bed:      {status.temp_bed:.0f}°C / {status.temp_bed_target:.0f}°C" if status.temp_bed else "    Bed: N/A")
        if status.materials:
            print(f"    Materials: {status.materials}")

    monitor = BambuLabMonitor("Test Bambu", config, status_callback=on_status)

    print("  Connecting via MQTT...")
    connected = monitor.connect()
    print(f"  Connected: {connected}")

    if connected:
        print("  Waiting for MQTT data (10 seconds)...")
        timeout = 10
        start = time.time()
        while (time.time() - start) < timeout:
            if last_status[0]:
                break
            time.sleep(0.5)

        if not last_status[0]:
            print("  No data received within 10 seconds")

    monitor.disconnect()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python tools/test_printer.py creality <IP>")
        print("  python tools/test_printer.py bambu <IP> <DEVICE_ID> <ACCESS_CODE>")
        sys.exit(1)

    printer_type = sys.argv[1].lower()
    ip = sys.argv[2]

    if printer_type == "creality":
        test_creality(ip)
    elif printer_type == "bambu":
        if len(sys.argv) < 5:
            print("Bambu requires: <IP> <DEVICE_ID> <ACCESS_CODE>")
            sys.exit(1)
        test_bambu(ip, sys.argv[3], sys.argv[4])
    else:
        print(f"Unknown type: {printer_type}. Use 'creality' or 'bambu'")
        sys.exit(1)
