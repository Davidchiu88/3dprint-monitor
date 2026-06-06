#!/usr/bin/env python3
"""Test Bambu FTP upload."""
import sys, io
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

from src.printer_control import _ImplicitFTP_TLS

test_gcode = b"; Test upload\nG28\nG1 X50 Y50 Z5 F3000\n"

for ip, code, name in [
    ('192.168.0.30', 'XXXXXXXX', 'A1 Mini'),
    ('192.168.0.58', 'XXXXXXXX', 'A1'),
]:
    print(f"\n=== {name} ({ip}) ===")
    try:
        ftp = _ImplicitFTP_TLS(printer_ip=ip)
        ftp.connect(ip, 990, timeout=8)
        print(f"  Connected: {ftp.getwelcome()[:50]}")
        ftp.login('bblp', code)
        print("  Login OK")
        ftp.prot_p()

        # Try upload
        print("  Trying STOR...")
        ftp.storbinary('STOR /user/test_bambu_upload.gcode', io.BytesIO(test_gcode))
        print("  UPLOAD SUCCESS!")

        # Try list to confirm
        files = []
        try:
            ftp.retrlines('NLST /user', files.append)
            found = any('test_bambu' in f for f in files)
            print(f"  File visible: {'YES' if found else 'no'}")
            # Cleanup
            if found:
                ftp.delete('/user/test_bambu_upload.gcode')
                print("  Cleaned up")
        except Exception as e:
            print(f"  List error (ok): {e}")

        ftp.close()
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
