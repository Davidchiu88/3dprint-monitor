#!/usr/bin/env python3
"""Test camera endpoints for all printers."""
import sys, requests, socket
sys.stdout.reconfigure(encoding='utf-8')

# K1C cameras
for ip, name in [('192.168.0.205','K1C Red'), ('192.168.0.92','K1C Black')]:
    print(f"\n=== {name} ({ip}) ===")
    for ep in ['/?action=snapshot', '/?action=stream', '/snapshot.jpg']:
        try:
            r = requests.get(f'http://{ip}:8080{ep}', timeout=3, stream=True)
            ct = r.headers.get('content-type','')
            size = len(r.content[:4096])
            r.close()
            print(f"  Port 8080{ep}: {r.status_code} {ct[:40]} ~{size}B")
        except Exception as e:
            print(f"  Port 8080{ep}: {str(e)[:50]}")

# Bambu camera ports
print("\n=== Bambu A1 Mini (192.168.0.30) ===")
for port in [322, 1935, 6000, 8554, 8080]:
    s = socket.socket()
    s.settimeout(1)
    r = s.connect_ex(('192.168.0.30', port))
    s.close()
    if r == 0:
        print(f"  Port {port}: OPEN")

# Check if ffmpeg/opencv available
print("\n=== Tools ===")
try:
    import subprocess
    r = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=3)
    print(f"  FFmpeg: available")
except:
    print(f"  FFmpeg: not found")

try:
    import cv2
    print(f"  OpenCV: {cv2.__version__}")
except:
    print(f"  OpenCV: not installed")

try:
    import av
    print(f"  PyAV: available")
except:
    print(f"  PyAV: not installed")
