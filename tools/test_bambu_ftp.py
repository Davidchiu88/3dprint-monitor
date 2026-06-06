#!/usr/bin/env python3
"""Test Bambu Lab FTP connection for file listing."""
import ssl, socket, ftplib, io, sys
sys.stdout.reconfigure(encoding='utf-8')

IP   = '192.168.0.30'
CODE = 'XXXXXXXX'

# ── 1. Port scan ─────────────────────────────────────────────────────
print("=== Port scan ===")
for port in [21, 990, 2121, 8821]:
    s = socket.socket()
    s.settimeout(2)
    r = s.connect_ex((IP, port))
    s.close()
    print(f"  Port {port}: {'OPEN' if r==0 else 'closed'}")

# ── 2. Try FTP port 21 (explicit TLS / plain) ─────────────────────────
print("\n=== Try port 21 (plain FTP) ===")
try:
    ftp = ftplib.FTP(timeout=5)
    ftp.connect(IP, 21)
    print(f"  Connected! Welcome: {ftp.getwelcome()[:60]}")
    try:
        ftp.login("bblp", CODE)
        print("  Login OK!")
        files = []
        ftp.retrlines("LIST", files.append)
        for f in files[:5]:
            print(f"  {f}")
    except Exception as e:
        print(f"  Login error: {e}")
    ftp.quit()
except Exception as e:
    print(f"  Connect error: {e}")

# ── 3. Try implicit TLS FTP (port 990) ───────────────────────────────
print("\n=== Try port 990 (implicit TLS FTP) ===")

class ImplicitFTP_TLS(ftplib.FTP_TLS):
    """FTP with implicit SSL on connection (port 990)."""
    def connect(self, host="", port=0, timeout=-999, source_address=None):
        if not port:
            port = 990
        self.source_address = source_address
        self.sock = socket.create_connection((host, port), self.timeout, source_address)
        self.sock = self.context.wrap_socket(self.sock, server_hostname=host)
        self.af = self.sock.family
        self.file = self.sock.makefile('r', encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
ctx.set_ciphers("ALL:@SECLEVEL=0")

try:
    ftp = ImplicitFTP_TLS(context=ctx)
    ftp.connect(IP, 990, timeout=8)
    print(f"  TLS connected! {ftp.getwelcome()[:60]}")
    ftp.login("bblp", CODE)
    print("  Login OK!")
    ftp.prot_p()
    dirs = []
    ftp.retrlines("LIST", dirs.append)
    print("  Root listing:")
    for d in dirs[:10]:
        print(f"    {d}")
    # Try /user
    try:
        ftp.cwd("/user")
        files = []
        ftp.retrlines("LIST", files.append)
        print(f"\n  /user listing ({len(files)} items):")
        for f in files[:10]:
            print(f"    {f}")
    except Exception as e:
        print(f"  /user error: {e}")
    ftp.quit()
except Exception as e:
    print(f"  Error: {e}")

# ── 4. Raw TCP peek on port 990 ───────────────────────────────────────
print("\n=== Raw peek port 990 ===")
try:
    s = socket.socket()
    s.settimeout(5)
    s.connect((IP, 990))
    # Wrap with SSL immediately
    ctx2 = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx2.check_hostname = False
    ctx2.verify_mode = ssl.CERT_NONE
    ctx2.options |= ssl.OP_LEGACY_SERVER_CONNECT
    ctx2.set_ciphers("ALL:@SECLEVEL=0")
    ss = ctx2.wrap_socket(s, server_hostname=IP)
    print(f"  SSL handshake OK! Cipher: {ss.cipher()}")
    # Read FTP banner
    data = ss.recv(256)
    print(f"  Banner: {data.decode(errors='replace')[:80]}")
    ss.close()
except Exception as e:
    print(f"  Error: {e}")
