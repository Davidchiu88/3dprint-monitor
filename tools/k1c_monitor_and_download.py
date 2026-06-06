#!/usr/bin/env python3
"""Monitor K1C printing status and auto-download files when done."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import time
import requests
import json
from datetime import datetime
from pathlib import Path

class K1CMonitor:
    def __init__(self, ip: str, name: str):
        self.ip = ip
        self.name = name
        self.api_url = f"http://{ip}:7125/api/printer"
        self.last_state = None
        self.print_history = []

    def get_status(self):
        """Get current printer status."""
        try:
            r = requests.get(self.api_url, timeout=3)
            return r.json() if r.status_code == 200 else None
        except:
            return None

    def is_printing(self, status):
        """Check if printer is currently printing."""
        if not status:
            return None
        state = status.get('print_job', {}).get('state', '').lower()
        return state in ['printing', 'paused']

    def get_current_file(self, status):
        """Get current file being printed."""
        if not status:
            return None
        return status.get('print_job', {}).get('filename', '')

    def download_via_ssh(self, filename: str, output_dir: str = "downloads"):
        """Download file via SSH (when printing is done)."""
        try:
            from src.printer_control import K1CController

            k1c = K1CController(self.ip)
            Path(output_dir).mkdir(exist_ok=True)

            print(f"  ⬇️  下載: {filename}")
            data = k1c.download_file(filename)

            if data:
                file_path = Path(output_dir) / filename
                file_path.write_bytes(data)
                size_mb = len(data) / 1024 / 1024
                print(f"  ✅ 已保存: {file_path} ({size_mb:.1f} MB)")
                return True
            else:
                print(f"  ❌ 下載失敗")
                return False
        except Exception as e:
            print(f"  ❌ 異常: {type(e).__name__}")
            return False

    def monitor_until_done(self, check_interval: int = 10, max_wait: int = 3600):
        """Monitor printer until current print is done."""
        print(f"\n{'='*60}")
        print(f"{self.name} - 列印監控")
        print(f"{'='*60}\n")

        start_time = time.time()
        last_file = None
        downloaded_files = set()

        while time.time() - start_time < max_wait:
            status = self.get_status()
            is_printing = self.is_printing(status)
            current_file = self.get_current_file(status)

            timestamp = datetime.now().strftime("%H:%M:%S")

            if is_printing is None:
                print(f"[{timestamp}] ⚠️  無法連接 API (列印中)")
            elif is_printing:
                progress = status.get('print_job', {}).get('print_progress', 0)
                print(f"[{timestamp}] 🖨️  列印中: {current_file} ({progress*100:.0f}%)")
                last_file = current_file
            else:
                if last_file and current_file != last_file:
                    print(f"[{timestamp}] ✅ 列印完成!")
                    print(f"  檔案: {last_file}")

                    # 嘗試下載完成的檔案
                    if last_file not in downloaded_files:
                        self.download_via_ssh(last_file)
                        downloaded_files.add(last_file)

                    print(f"\n  監控結束")
                    return True
                elif current_file:
                    print(f"[{timestamp}] ⏸️  就緒: {current_file}")

            time.sleep(check_interval)

        print(f"\n❌ 超時: 等待超過 {max_wait} 秒")
        return False

# ─── 主程式 ────────────────────────────────────

if __name__ == '__main__':
    import sys
    import os

    # 可選指定機器
    if len(sys.argv) > 1:
        k1c_name = sys.argv[1]
        k1c_ips = {
            '红': '192.168.0.205',
            '黑': '192.168.0.92',
            'red': '192.168.0.205',
            'black': '192.168.0.92',
        }
        ip = k1c_ips.get(k1c_name.lower())
        if not ip:
            print(f"未知機器: {k1c_name}")
            sys.exit(1)
    else:
        # 監控兩台
        ips = [
            ('K1C 紅', '192.168.0.205'),
            ('K1C 黑', '192.168.0.92'),
        ]

        for name, ip in ips:
            monitor = K1CMonitor(ip, name)
            monitor.monitor_until_done()
            time.sleep(2)

        sys.exit(0)

    # 監控指定機器
    monitor = K1CMonitor(ip, f"K1C {k1c_name}")
    monitor.monitor_until_done()
