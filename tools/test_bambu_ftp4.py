#!/usr/bin/env python3
"""Probe Bambu A1 Mini FTP capabilities."""
import sys, ftplib
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from src.printer_control import _ImplicitFTP_TLS

ip, code = '192.168.0.30', 'XXXXXXXX'

ftp = _ImplicitFTP_TLS(printer_ip=ip)
ftp.connect(ip, 990, timeout=8)
ftp.login('bblp', code)
ftp.prot_p()
print("Connected!")

# PWD - what is current directory?
try:
    print(f"PWD: {ftp.pwd()}")
except Exception as e:
    print(f"PWD error: {e}")

# FEAT - what features does the server support?
try:
    ftp.sendcmd('FEAT')
    print("FEAT supported")
except Exception as e:
    print(f"FEAT: {e}")

# Try MLSD (newer listing)
try:
    entries = list(ftp.mlsd())
    print(f"MLSD root: {entries[:3]}")
except Exception as e:
    print(f"MLSD: {e}")

# NLST (simpler listing)
try:
    files = ftp.nlst()
    print(f"NLST root: {files[:5]}")
except Exception as e:
    print(f"NLST root: {e}")

# Try SIZE on a known file (if we can upload first)
# Try STOR - can we upload?
import io
test_data = b"test content"
try:
    ftp.storbinary("STOR /test_probe.txt", io.BytesIO(test_data))
    print("STOR /test_probe.txt: SUCCESS!")
    # Now try to list
    try:
        ftp.delete("/test_probe.txt")
        print("DELETE: success")
    except: pass
except Exception as e:
    print(f"STOR /test_probe.txt: {e}")

# Try upload to / (root)
try:
    ftp.storbinary("STOR test_probe.txt", io.BytesIO(test_data))
    print("STOR test_probe.txt (no path): SUCCESS!")
    # Try to find it
    try:
        ftp.retrlines("LIST", lambda l: print(f"  {l}"))
    except Exception as e2:
        print(f"  LIST after upload: {e2}")
    try:
        ftp.delete("test_probe.txt")
    except: pass
except Exception as e:
    print(f"STOR test_probe.txt: {e}")

try: ftp.close()
except: pass
