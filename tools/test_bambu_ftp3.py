#!/usr/bin/env python3
"""Explore Bambu A1 Mini FTP directory structure."""
import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from src.printer_control import _ImplicitFTP_TLS

ip, code = '192.168.0.30', 'XXXXXXXX'

ftp = _ImplicitFTP_TLS(printer_ip=ip)
ftp.connect(ip, 990, timeout=8)
ftp.login('bblp', code)
ftp.prot_p()
print(f"Connected! Welcome: {ftp.getwelcome()}")

# Try listing root
for path in ['/', '/user', '/sdcard', '/SD_card', '/cache', '/storage', '/mnt', '/data']:
    try:
        files = []
        ftp.retrlines(f'LIST {path}', files.append)
        print(f"\n{path}: {len(files)} items")
        for f in files[:5]:
            print(f"  {f}")
    except Exception as e:
        print(f"{path}: {e}")

ftp.quit()
