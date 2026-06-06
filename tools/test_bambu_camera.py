#!/usr/bin/env python3
"""
Test Bambu Lab A1/A1 Mini camera via port 6000 (JPEG frame stream).
Based on: https://github.com/mattcar15/bambu-connect

Auth: TLS socket + 80-byte custom auth packet
  [4B payload_size=0x40][4B type=0x3000][4B flags=0][4B null]
  [32B username=bblp][32B password=access_code]
"""
import ssl, socket, struct, sys, time

sys.stdout.reconfigure(encoding='utf-8')

PRINTERS = [
    {'name': 'A1 Mini', 'ip': '192.168.0.30', 'code': 'XXXXXXXX'},
    {'name': 'A1',      'ip': '192.168.0.58', 'code': 'XXXXXXXX'},
]

def make_auth_packet(username: str, password: str) -> bytes:
    packet = bytearray(80)
    struct.pack_into('<I', packet,  0, 0x40)    # payload size
    struct.pack_into('<I', packet,  4, 0x3000)  # type id
    struct.pack_into('<I', packet,  8, 0)       # flags
    struct.pack_into('<I', packet, 12, 0)       # null
    u = username.encode('utf-8')[:32]
    p = password.encode('utf-8')[:32]
    packet[16:16+len(u)] = u
    packet[48:48+len(p)] = p
    return bytes(packet)


def recv_exact(sock, n: int) -> bytes:
    """Receive exactly n bytes from socket."""
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(min(65536, n - len(buf)))
        if not chunk:
            raise ConnectionError("Connection closed")
        buf += chunk
    return buf


def capture_frame(ip: str, code: str, timeout: int = 20) -> bytes | None:
    """
    Connect to Bambu port 6000 and read one JPEG frame.
    Protocol:
      1. TLS connect
      2. Send 80-byte auth packet
      3. Read stream of: [16B header][payload_size B JPEG data]
         header[0:4] = payload_size (little-endian uint32)
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode   = ssl.CERT_NONE

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    tls = ctx.wrap_socket(sock, server_hostname=ip)

    try:
        tls.connect((ip, 6000))
        print(f"  TLS connected! Cipher: {tls.cipher()[0]}")
        tls.send(make_auth_packet('bblp', code))

        # Read framed data: 16-byte header then payload
        deadline = time.time() + timeout
        while time.time() < deadline:
            # Read 16-byte frame header
            header = recv_exact(tls, 16)
            payload_size = struct.unpack_from('<I', header, 0)[0]
            print(f"  Frame header: payload={payload_size} bytes")

            if payload_size == 0 or payload_size > 10_000_000:
                print(f"  Skip: unusual payload size")
                continue

            # Read exactly payload_size bytes (the JPEG)
            payload = recv_exact(tls, payload_size)

            # Validate it's JPEG
            if payload[:2] == b'\xff\xd8':
                print(f"  Got JPEG frame: {len(payload)} bytes")
                return payload
            else:
                print(f"  Not JPEG: {payload[:8].hex()}")

    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")
    finally:
        try: tls.close()
        except: pass
    return None


for p in PRINTERS:
    print(f"\n=== {p['name']} ({p['ip']}) ===")
    img = capture_frame(p['ip'], p['code'])
    if img:
        fname = f"data/cam_{p['name'].replace(' ','_')}.jpg"
        with open(fname, 'wb') as f:
            f.write(img)
        print(f"  Saved {len(img)} bytes → {fname}")
    else:
        print("  No frame received")
