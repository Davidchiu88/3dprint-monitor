#!/usr/bin/env python3
"""樹梅派遠程管理工具 - SSH 遠程控制和監控。"""

import sys
import os
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

try:
    import paramiko
except ImportError:
    print("❌ 需要 paramiko 庫")
    print("安裝: pip install paramiko")
    sys.exit(1)


class RaspberryPiManager:
    """樹梅派遠程管理器。"""

    def __init__(self, host: str, username: str = "pi", password: str = None, key_file: str = None):
        """初始化連接。"""
        self.host = host
        self.username = username
        self.password = password
        self.key_file = key_file
        self.ssh = None
        self.sftp = None

    def connect(self):
        """建立 SSH 連接。"""
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if self.key_file and os.path.exists(self.key_file):
                self.ssh.connect(self.host, username=self.username, key_filename=self.key_file)
            else:
                self.ssh.connect(self.host, username=self.username, password=self.password)

            self.sftp = self.ssh.open_sftp()
            print(f"✅ 已連接到 {self.host}")
            return True
        except Exception as e:
            print(f"❌ 連接失敗: {e}")
            return False

    def disconnect(self):
        """斷開連接。"""
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        print("已斷開連接")

    def execute(self, command: str) -> tuple:
        """執行遠程命令。"""
        try:
            stdin, stdout, stderr = self.ssh.exec_command(command)
            return stdout.read().decode("utf-8", errors="replace"), stderr.read().decode("utf-8", errors="replace")
        except Exception as e:
            return "", str(e)

    def execute_sudo(self, command: str, password: str = None) -> tuple:
        """執行需要 sudo 的命令。"""
        if not password:
            password = self.password
        cmd = f"echo '{password}' | sudo -S {command}"
        return self.execute(cmd)

    def get_status(self) -> dict:
        """取得系統狀態。"""
        status = {}

        # CPU 溫度
        out, _ = self.execute("vcgencmd measure_temp")
        status["temperature"] = out.strip()

        # 記憶體使用
        out, _ = self.execute("free -h | grep Mem")
        status["memory"] = out.strip()

        # 磁盤使用
        out, _ = self.execute("df -h / | tail -1")
        status["disk"] = out.strip()

        # 運行時間
        out, _ = self.execute("uptime")
        status["uptime"] = out.strip()

        # CPU 使用率
        out, _ = self.execute("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'")
        status["cpu_usage"] = out.strip()

        return status

    def get_service_status(self, service: str) -> dict:
        """取得服務狀態。"""
        cmd = f"systemctl status {service}"
        out, _ = self.execute(cmd)

        return {
            "service": service,
            "status": out,
            "running": "running" in out.lower() or "active" in out.lower(),
        }

    def restart_service(self, service: str) -> bool:
        """重啟服務。"""
        out, err = self.execute_sudo(f"systemctl restart {service}")
        if err and "password" not in err.lower():
            print(f"❌ 重啟失敗: {err}")
            return False
        print(f"✅ {service} 已重啟")
        return True

    def start_service(self, service: str) -> bool:
        """啟動服務。"""
        out, err = self.execute_sudo(f"systemctl start {service}")
        if err and "password" not in err.lower():
            print(f"❌ 啟動失敗: {err}")
            return False
        print(f"✅ {service} 已啟動")
        return True

    def stop_service(self, service: str) -> bool:
        """停止服務。"""
        out, err = self.execute_sudo(f"systemctl stop {service}")
        if err and "password" not in err.lower():
            print(f"❌ 停止失敗: {err}")
            return False
        print(f"✅ {service} 已停止")
        return True

    def get_logs(self, service: str, lines: int = 50) -> str:
        """取得服務日誌。"""
        cmd = f"journalctl -u {service} -n {lines} --no-pager"
        out, _ = self.execute(cmd)
        return out

    def download_file(self, remote_path: str, local_path: str):
        """下載檔案。"""
        try:
            self.sftp.get(remote_path, local_path)
            print(f"✅ 已下載: {remote_path} → {local_path}")
            return True
        except Exception as e:
            print(f"❌ 下載失敗: {e}")
            return False

    def upload_file(self, local_path: str, remote_path: str):
        """上傳檔案。"""
        try:
            self.sftp.put(local_path, remote_path)
            print(f"✅ 已上傳: {local_path} → {remote_path}")
            return True
        except Exception as e:
            print(f"❌ 上傳失敗: {e}")
            return False

    def test_printers(self) -> dict:
        """測試印表機連接。"""
        results = {}

        # 執行測試腳本
        cmd = "cd /home/pi/3dprint && python3 tools/check_k1c_files.py 2>&1"
        out, _ = self.execute(cmd)
        results["k1c"] = out

        cmd = "cd /home/pi/3dprint && python3 tools/check_bambu_files.py 2>&1"
        out, _ = self.execute(cmd)
        results["bambu"] = out

        return results

    def get_api_status(self) -> dict:
        """取得 API 狀態。"""
        cmd = "curl -s http://localhost:7000/api/status | python3 -m json.tool"
        out, err = self.execute(cmd)

        if err:
            return {"error": err}

        try:
            return json.loads(out)
        except:
            return {"raw": out}


# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="樹梅派遠程管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python3 raspberry_pi_manager.py -H 192.168.1.100 -u pi -p password status
  python3 raspberry_pi_manager.py -H pi@192.168.1.100 restart-monitor
  python3 raspberry_pi_manager.py -H pi@192.168.1.100 logs printer-monitor 100
  python3 raspberry_pi_manager.py -H pi@192.168.1.100 test-printers
  python3 raspberry_pi_manager.py -H pi@192.168.1.100 download-log
        """,
    )

    parser.add_argument(
        "-H", "--host", required=True, help="樹梅派地址 (IP 或 user@IP)"
    )
    parser.add_argument("-u", "--username", default="pi", help="用戶名 (預設: pi)")
    parser.add_argument("-p", "--password", help="密碼")
    parser.add_argument("-k", "--key", help="私鑰檔案路徑")

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # 狀態命令
    subparsers.add_parser("status", help="查看系統狀態")
    subparsers.add_parser("api-status", help="查看 API 狀態")

    # 服務命令
    service_parser = subparsers.add_parser("service-status", help="查看服務狀態")
    service_parser.add_argument("service", help="服務名 (printer-monitor/printer-api)")

    subparsers.add_parser("restart-monitor", help="重啟監控系統")
    subparsers.add_parser("restart-api", help="重啟 API 伺服器")
    subparsers.add_parser("restart-all", help="重啟所有服務")

    subparsers.add_parser("start-monitor", help="啟動監控系統")
    subparsers.add_parser("stop-monitor", help="停止監控系統")

    # 日誌命令
    logs_parser = subparsers.add_parser("logs", help="查看日誌")
    logs_parser.add_argument("service", help="服務名")
    logs_parser.add_argument("-n", "--lines", type=int, default=50, help="行數 (預設: 50)")

    # 檔案命令
    download_parser = subparsers.add_parser("download-log", help="下載日誌檔")
    download_parser.add_argument(
        "-o", "--output", default="printer_monitor.log", help="輸出路徑"
    )

    # 測試命令
    subparsers.add_parser("test-printers", help="測試印表機連接")

    args = parser.parse_args()

    # 解析 host
    if "@" in args.host:
        username, host = args.host.split("@")
        args.username = username
        args.host = host

    # 連接
    print(f"連接 {args.username}@{args.host}...")
    manager = RaspberryPiManager(args.host, args.username, args.password, args.key)

    if not manager.connect():
        sys.exit(1)

    try:
        # 執行命令
        if args.command == "status":
            print("\n=== 系統狀態 ===\n")
            status = manager.get_status()
            for key, value in status.items():
                print(f"{key:15} {value}")

        elif args.command == "api-status":
            print("\n=== API 狀態 ===\n")
            status = manager.get_api_status()
            print(json.dumps(status, indent=2, ensure_ascii=False))

        elif args.command == "service-status":
            print(f"\n=== {args.service} 狀態 ===\n")
            status = manager.get_service_status(args.service)
            print(f"狀態: {'✅ 運行中' if status['running'] else '❌ 已停止'}")
            print(status["status"])

        elif args.command == "restart-monitor":
            manager.restart_service("printer-monitor.service")

        elif args.command == "restart-api":
            manager.restart_service("printer-api.service")

        elif args.command == "restart-all":
            manager.restart_service("printer-monitor.service")
            manager.restart_service("printer-api.service")

        elif args.command == "start-monitor":
            manager.start_service("printer-monitor.service")

        elif args.command == "stop-monitor":
            manager.stop_service("printer-monitor.service")

        elif args.command == "logs":
            print(f"\n=== {args.service} 日誌 (最後 {args.lines} 行) ===\n")
            logs = manager.get_logs(args.service, args.lines)
            print(logs)

        elif args.command == "download-log":
            manager.download_file(
                "/home/pi/3dprint/printer_monitor.log", args.output
            )

        elif args.command == "test-printers":
            print("\n=== 測試印表機連接 ===\n")
            results = manager.test_printers()
            for name, result in results.items():
                print(f"\n【{name.upper()}】\n{result}")

        else:
            print("❌ 未知命令")

    finally:
        manager.disconnect()


if __name__ == "__main__":
    main()
