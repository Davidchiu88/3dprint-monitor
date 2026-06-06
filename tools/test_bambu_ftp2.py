#!/usr/bin/env python3
"""Test Bambu FTP with PASV fix."""
import sys, socket, select as sel
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

from src.printer_control import _ImplicitFTP_TLS

PRINTERS = [
    ('Bambu A1 Mini', '192.168.0.30', 'XXXXXXXX'),
    ('Bambu A1',      '192.168.0.58', 'XXXXXXXX'),
]

for name, ip, code in PRINTERS:
    print(f"\n=== {name} ({ip}) ===")

    # Port check
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setblocking(False)
    s.connect_ex((ip, 990))
    ok = bool(sel.select([], [s], [s], 2.0)[1])
    s.close()
    print(f"  Port 990: {'OPEN' if ok else 'CLOSED'}")

    if not ok:
        print("  Skipping FTP test (port closed)")
        continue

    # FTP test with PASV fix
    try:
        ftp = _ImplicitFTP_TLS(printer_ip=ip)
        ftp.connect(ip, 990, timeout=8)
        print(f"  FTP connected: {ftp.getwelcome()[:60]}")
        ftp.login('bblp', code)
        print("  Login OK!")
        ftp.prot_p()

        # List /user directory
        files = []
        try:
            ftp.retrlines('LIST /user', files.append)
            print(f"  Files in /user ({len(files)}):")
            for f in files[:5]:
                print(f"    {f}")
        except Exception as e:
            print(f"  LIST error: {e}")

        ftp.quit()
    except Exception as e:
        print(f"  FTP error: {type(e).__name__}: {e}")
