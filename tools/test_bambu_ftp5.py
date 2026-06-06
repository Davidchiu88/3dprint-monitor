#!/usr/bin/env python3
"""Clean FTP test after cooldown."""
import sys, io, time
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from src.printer_control import _ImplicitFTP_TLS

ip, code = '192.168.0.30', 'XXXXXXXX'
print(f"Testing Bambu A1 Mini FTP at {ip}:990")

try:
    ftp = _ImplicitFTP_TLS(printer_ip=ip)
    ftp.connect(ip, 990, timeout=15)
    print(f"Connected! {ftp.getwelcome()[:60]}")
    ftp.login('bblp', code)
    print("Login OK!")
    ftp.prot_p()

    # Try NLST root
    for path in ['', '/', '/user', '/sdcard']:
        try:
            items = ftp.nlst(path)
            print(f"NLST '{path}': {items[:5]}")
        except Exception as e:
            print(f"NLST '{path}': {str(e)[:50]}")

    # Try upload to /user
    try:
        ftp.storbinary('STOR /user/test_upload.gcode', io.BytesIO(b'; test\nG28\n'))
        print("STOR /user/test_upload.gcode: SUCCESS!")
        # Verify with NLST
        items = ftp.nlst('/user')
        print(f"After upload, NLST /user: {items[:5]}")
        # Cleanup
        try: ftp.delete('/user/test_upload.gcode')
        except: pass
    except Exception as e:
        print(f"STOR /user/...: {str(e)[:80]}")

    ftp.close()
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)[:100]}")
