#!/usr/bin/env python3
"""完整的拓竹檔案下載工具 - 從 FTP 直接下載到本地磁盤。"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import ftplib
import ssl
import time
import socket
from pathlib import Path
from datetime import datetime

class BambuDownloader:
    def __init__(self, ip: str, device_id: str, access_code: str, name: str):
        self.ip = ip
        self.device_id = device_id
        self.access_code = access_code
        self.name = name
        self.download_dir = Path("downloads") / name.replace(" ", "_")
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def create_ftp_context(self):
        """建立 SSL 上下文。"""
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        ctx.set_ciphers("ALL:@SECLEVEL=0")
        return ctx

    def list_files(self):
        """列出 FTP 上的檔案。"""
        try:
            print(f"\n  連接 FTP ({self.ip}:990)...", end=" ", flush=True)
            ctx = self.create_ftp_context()

            # Custom FTP class to handle implicit TLS
            class BambuFTP(ftplib.FTP_TLS):
                def __init__(self, printer_ip):
                    self._printer_ip = printer_ip
                    super().__init__(context=ctx)

                def connect(self, host="", port=0, timeout=-999, source_address=None):
                    if not port:
                        port = 990
                    if host:
                        self.host = host
                    self.source_address = source_address
                    t = (self.timeout if self.timeout != -999 else 10) if timeout == -999 else timeout
                    import socket as _s
                    raw = _s.create_connection((host or self.host, port), t, source_address)
                    self.sock = self.context.wrap_socket(raw, server_hostname=self.host)
                    self.af = self.sock.family
                    self.file = self.sock.makefile("r", encoding=self.encoding)
                    self.welcome = self.getresp()
                    return self.welcome

            ftp = BambuFTP(self.ip)
            ftp.connect(self.ip, 990, timeout=15)
            print("✅", flush=True)

            print(f"  登錄 (bblp/{self.access_code[:4]}...)...", end=" ", flush=True)
            ftp.auth()
            ftp.login("bblp", self.access_code)
            ftp.prot_p()
            print("✅", flush=True)

            # 列表檔案
            files = []
            for search_dir in ["/cache", "/model", "", "/user"]:
                try:
                    print(f"  搜尋 {search_dir if search_dir else '/'} ...", end=" ", flush=True)
                    entries = ftp.nlst(search_dir) if search_dir else ftp.nlst()

                    for item in entries:
                        name = item.split("/")[-1]
                        if any(name.lower().endswith(ext) for ext in (".gcode", ".3mf", ".bgcode")):
                            # Normalize path
                            if item.startswith("/"):
                                path = item
                            elif "/" in item:
                                path = f"/{item}"
                            elif search_dir:
                                path = f"{search_dir}/{item}"
                            else:
                                path = f"/{item}"
                            files.append((name, path))

                    if files:
                        print(f"✅ 找到 {len(files)} 個檔案")
                        break
                except ftplib.all_errors:
                    print("❌", flush=True)
                    continue

            ftp.quit()
            return files

        except socket.timeout:
            print(f"⏱️  超時 (15s)")
            return []
        except Exception as e:
            print(f"❌ {type(e).__name__}: {str(e)[:50]}")
            return []

    def download_file(self, remote_path: str, filename: str):
        """下載單個檔案。"""
        try:
            ctx = self.create_ftp_context()

            class BambuFTP(ftplib.FTP_TLS):
                def __init__(self, printer_ip):
                    self._printer_ip = printer_ip
                    super().__init__(context=ctx)

                def connect(self, host="", port=0, timeout=-999, source_address=None):
                    if not port:
                        port = 990
                    if host:
                        self.host = host
                    self.source_address = source_address
                    t = (self.timeout if self.timeout != -999 else 10) if timeout == -999 else timeout
                    import socket as _s
                    raw = _s.create_connection((host or self.host, port), t, source_address)
                    self.sock = self.context.wrap_socket(raw, server_hostname=self.host)
                    self.af = self.sock.family
                    self.file = self.sock.makefile("r", encoding=self.encoding)
                    self.welcome = self.getresp()
                    return self.welcome

            ftp = BambuFTP(self.ip)
            ftp.connect(self.ip, 990, timeout=30)
            ftp.auth()
            ftp.login("bblp", self.access_code)
            ftp.prot_p()

            # 下載檔案
            local_path = self.download_dir / filename
            print(f"    ⬇️  {filename[:50]}...", end=" ", flush=True)

            size = 0
            t0 = time.time()

            def callback(chunk):
                nonlocal size
                size += len(chunk)

            with open(local_path, 'wb') as f:
                ftp.retrbinary(f"RETR {remote_path}", lambda chunk: (f.write(chunk), callback(chunk)))

            elapsed = time.time() - t0
            size_mb = size / 1024 / 1024

            print(f"✅ ({size_mb:.1f} MB in {elapsed:.1f}s)")

            ftp.quit()
            return True

        except Exception as e:
            print(f"❌ {type(e).__name__}")
            return False

# ─── 主程式 ────────────────────────────────────

if __name__ == '__main__':
    print("=" * 70)
    print("拓竹 Bambu Lab 檔案下載器")
    print("=" * 70)

    configs = [
        ('Bambu A1 Mini', '192.168.0.30', 'XXXXXXXXXXXXXXX', 'XXXXXXXX'),
        ('Bambu A1', '192.168.0.58', 'XXXXXXXXXXXXXXX', 'XXXXXXXX'),
        ('Bambu A1 #2', '192.168.0.70', 'XXXXXXXXXXXXXXX', 'XXXXXXXX'),
    ]

    for name, ip, device_id, access_code in configs:
        print(f"\n### {name}\n")

        downloader = BambuDownloader(ip, device_id, access_code, name)

        # 列表檔案
        files = downloader.list_files()

        if not files:
            print(f"  ⚠️  無法獲取檔案列表")
            continue

        # 下載前 3 個檔案
        print(f"\n  下載前 3 個檔案:")
        for fname, fpath in files[:3]:
            downloader.download_file(fpath, fname)

        print(f"\n  保存位置: {downloader.download_dir}")

    print("\n" + "=" * 70)
    print("下載完成")
    print("=" * 70)
