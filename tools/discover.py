#!/usr/bin/env python3
"""
Printer Discovery Tool
Scans local network for Creality (port 7125) and Bambu Lab (port 8883) printers
"""

import ipaddress
import json
import socket
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Optional
import requests


def get_local_subnet() -> Optional[str]:
    """Detect current machine's local subnet"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        # Assume /24 subnet
        parts = local_ip.rsplit(".", 1)
        return parts[0] + ".0/24"
    except Exception:
        return None


def check_creality(ip: str) -> Optional[Dict]:
    """Check if an IP is a Creality K1C printer via Moonraker API"""
    try:
        url = f"http://{ip}:7125/api/printer"
        resp = requests.get(url, timeout=1.5)
        if resp.status_code == 200:
            data = resp.json()
            name = "Unknown"
            if "info" in data:
                name = data["info"].get("hostname", f"Creality @ {ip}")
            return {
                "type": "creality_k1c",
                "ip": ip,
                "name": name,
                "api_response": data,
            }
    except Exception:
        pass
    return None


def check_bambu(ip: str) -> Optional[Dict]:
    """Check if an IP has port 8883 open (likely Bambu Lab printer)"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        result = sock.connect_ex((ip, 8883))
        sock.close()
        if result == 0:
            return {
                "type": "bambu_lab",
                "ip": ip,
                "name": f"Bambu Lab @ {ip}",
                "note": "Port 8883 open - requires device_id and access_code",
            }
    except Exception:
        pass
    return None


def scan_ip(ip: str) -> List[Dict]:
    """Scan a single IP for both printer types"""
    results = []

    creality = check_creality(ip)
    if creality:
        results.append(creality)

    bambu = check_bambu(ip)
    if bambu:
        results.append(bambu)

    return results


def scan_network(subnet: str = None) -> List[Dict]:
    """Scan entire subnet for printers"""
    if not subnet:
        subnet = get_local_subnet()
        if not subnet:
            print("Could not detect local subnet, using 192.168.1.0/24")
            subnet = "192.168.1.0/24"

    network = ipaddress.IPv4Network(subnet, strict=False)
    hosts = list(network.hosts())

    print(f"\nScanning {len(hosts)} addresses on {subnet}...")
    print("Looking for Bambu Lab (port 8883) and Creality K1C (port 7125)...\n")

    found = []
    scanned = 0

    with ThreadPoolExecutor(max_workers=64) as executor:
        futures = {executor.submit(scan_ip, str(ip)): str(ip) for ip in hosts}

        for future in as_completed(futures):
            scanned += 1
            if scanned % 50 == 0:
                print(f"  Progress: {scanned}/{len(hosts)}...")

            results = future.result()
            if results:
                for r in results:
                    print(f"\n  FOUND: {r['type'].upper()} at {r['ip']}")
                    found.append(r)

    return found


def print_results(found: List[Dict]) -> None:
    """Print scan results and generate YAML snippet"""
    if not found:
        print("\nNo printers found on the network.")
        print("\nTips:")
        print("  - Check if printers are turned on and connected to Wi-Fi")
        print("  - Try a different subnet: python tools/discover.py 192.168.0.0/24")
        return

    print(f"\n{'='*60}")
    print(f"Found {len(found)} printer(s):")
    print("="*60)

    for p in found:
        print(f"\n  {p['type'].upper()}")
        print(f"  IP: {p['ip']}")
        if p.get("name"):
            print(f"  Name: {p['name']}")
        if p.get("note"):
            print(f"  Note: {p['note']}")

    print(f"\n{'='*60}")
    print("config/printers.yaml snippet:")
    print("="*60)
    print("\nprinters:")

    bambu_count = 1
    creality_count = 1

    for p in found:
        if p["type"] == "bambu_lab":
            print(f"  - name: \"Bambu Lab #{bambu_count}\"")
            print(f"    type: \"bambu_lab\"")
            print(f"    ip: \"{p['ip']}\"")
            print(f"    device_id: \"FILL_IN_DEVICE_ID\"")
            print(f"    access_code: \"FILL_IN_ACCESS_CODE\"")
            bambu_count += 1
        elif p["type"] == "creality_k1c":
            print(f"  - name: \"Creality K1C #{creality_count}\"")
            print(f"    type: \"creality_k1c\"")
            print(f"    ip: \"{p['ip']}\"")
            creality_count += 1
        print()


if __name__ == "__main__":
    subnet = sys.argv[1] if len(sys.argv) > 1 else None

    print("3D Printer Discovery Tool")
    print("="*60)

    if subnet:
        print(f"Scanning subnet: {subnet}")
    else:
        detected = get_local_subnet()
        print(f"Detected local subnet: {detected or 'unknown'}")

    found = scan_network(subnet)
    print_results(found)
