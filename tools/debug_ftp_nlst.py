#!/usr/bin/env python3
"""Debug what ftp.nlst actually returns for Bambu A1 Mini."""
import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from src.printer_control import _ImplicitFTP_TLS

ip, code = '192.168.0.30', 'XXXXXXXX'
ftp = _ImplicitFTP_TLS(printer_ip=ip)
ftp.connect(ip, 990, timeout=8)
ftp.login('bblp', code); ftp.prot_p()

for d in ['/cache', '/model', '']:
    try:
        items = ftp.nlst(d) if d else ftp.nlst()
        gcode = [i for i in items if '.gcode' in i.lower() or '.3mf' in i.lower()]
        print(f"\nnlst('{d}') - first 3 gcode items:")
        for item in gcode[:3]:
            print(f"  repr: {item!r}")
            print(f"  starts_with_/: {item.startswith('/')}")
            print(f"  has /: {'/' in item}")
        if not gcode:
            print(f"  (no gcode files, total: {len(items)})")
    except Exception as e:
        print(f"nlst('{d}'): {e}")

ftp.close()
