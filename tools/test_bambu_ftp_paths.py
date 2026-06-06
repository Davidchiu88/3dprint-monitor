#!/usr/bin/env python3
"""Test Bambu FTP with different paths."""
import sys, io
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

from src.printer_control import _ImplicitFTP_TLS

ip, code = '192.168.0.30', 'XXXXXXXX'
test_data = b"; test\nG28\n"

ftp = _ImplicitFTP_TLS(printer_ip=ip)
ftp.connect(ip, 990, timeout=8)
ftp.login('bblp', code)
ftp.prot_p()
print(f"Connected: {ftp.getwelcome()[:50]}")
print(f"CWD: {ftp.pwd()!r}")

# Try NLST on different paths
for path in ['/', '/user', '/model', '/cache', '/sdcard', '']:
    try:
        items = ftp.nlst(path)
        print(f"NLST '{path}': {items[:3]}")
    except Exception as e:
        print(f"NLST '{path}': {str(e)[:50]}")

# Try STOR to different paths
for path in ['/model/test.gcode', '/cache/test.gcode', 'test.gcode', '/test.gcode']:
    try:
        ftp.storbinary(f'STOR {path}', io.BytesIO(test_data))
        print(f"STOR '{path}': SUCCESS!")
        try: ftp.delete(path)
        except: pass
    except Exception as e:
        print(f"STOR '{path}': {str(e)[:50]}")

ftp.close()
