#!/usr/bin/env python3
"""Direct file download test for K1C and Bambu Lab."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import yaml
from pathlib import Path

# Load config
cfg = yaml.safe_load(open("config/printers.yaml", encoding="utf-8"))
printers = {p['name']: p for p in cfg.get('printers', [])}

print("=" * 60)
print("3D 印表機檔案下載測試")
print("=" * 60)

# Test K1C
print("\n### Creality K1C 測試\n")
for name in ["Creality K1C 紅", "Creality K1C 黑"]:
    if name not in printers:
        continue

    p = printers[name]
    ip = p['ip']
    print(f"{name} ({ip}):")

    from src.printer_control import K1CController
    k1c = K1CController(ip)

    # First get file list
    try:
        print(f"  📋 獲取檔案列表...")
        from src.printer_control import K1CController as KC
        # Check file list first
        import requests
        r = requests.get(f'http://{ip}/downloads/humbnail/', timeout=5)
        import re
        items = re.findall(
            r'href="([^"./][^"]*\.png)"',
            r.text
        )
        if items:
            fname = items[0]
            print(f"  ✅ 找到 {len(items)} 個檔案")

            # Try to download first file
            gcode_name = fname.replace('.png', '.gcode')
            print(f"  ⬇️  嘗試下載: {gcode_name}")

            import time
            t0 = time.time()
            data = k1c.download_file(gcode_name)
            elapsed = time.time() - t0

            if data:
                print(f"  ✅ 下載成功: {len(data)} bytes in {elapsed:.1f}s")
            else:
                print(f"  ❌ 下載失敗 ({elapsed:.1f}s)")
        else:
            print(f"  ⚠️  未找到檔案")
    except Exception as e:
        print(f"  ❌ 錯誤: {type(e).__name__}: {str(e)[:60]}")

# Test Bambu Lab
print("\n### Bambu Lab 測試\n")
for name in ["Bambu A1 Mini", "Bambu A1", "Bambu A1 #2"]:
    if name not in printers:
        continue

    p = printers[name]
    ip = p['ip']
    did = p.get('device_id', '')
    ac = p.get('access_code', '')

    print(f"{name} ({ip}):")

    from src.printer_control import BambuController
    bambu = BambuController(ip, did, ac)

    try:
        # Check if printer is reachable
        import socket
        sock = socket.create_connection((ip, 8883), timeout=3)
        sock.close()
        print(f"  ✅ 連接 MQTT 伺服器成功 (port 8883)")

        # Try FTP
        try:
            import ftplib, ssl
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            ftp = ftplib.FTP_TLS(context=ctx, timeout=5)
            ftp.connect(ip, 990)
            ftp.auth()
            ftp.login('bblp', ac)

            # List cache directory
            items = []
            def callback(line):
                items.append(line)
            ftp.dir('/cache', callback)
            ftp.quit()

            gcode_items = [x for x in items if '.gcode' in x or '.3mf' in x]
            if gcode_items:
                print(f"  ✅ FTP 連接成功, 找到 {len(gcode_items)} 個相關檔案")
                print(f"     - 可下載")
            else:
                print(f"  ⚠️  FTP 連接成功，但無相關檔案")
        except Exception as e:
            print(f"  ⚠️  FTP 連接失敗: {type(e).__name__}")

    except Exception as e:
        print(f"  ❌ 無法連接: {type(e).__name__}: {str(e)[:50]}")

print("\n" + "=" * 60)
print("測試完成")
print("=" * 60)
