#!/usr/bin/env python3
"""Diagnostic and recovery tool for K1C black SSH issues."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import asyncio
import json
import socket
import time
import requests

IP = "192.168.0.92"
WS_PORT = 9999
SSH_PORT = 22

print("=" * 70)
print("K1C 黑 SSH 診斷和修復工具")
print("=" * 70)

# Step 1: Check connectivity
print(f"\n[1] 檢查連接...\n")

def check_port(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex((IP, port))
        s.close()
        return result == 0
    except:
        return False

http_ok = check_port(80)
ws_ok = check_port(WS_PORT)
ssh_ok = check_port(SSH_PORT)

print(f"  HTTP (80):       {'✅' if http_ok else '❌'}")
print(f"  WebSocket (9999): {'✅' if ws_ok else '❌'}")
print(f"  SSH (22):        {'✅' if ssh_ok else '❌'}")

if not http_ok:
    print(f"\n❌ 印表機離線 (HTTP 不可達)")
    sys.exit(1)

# Step 2: Check printer status
print(f"\n[2] 檢查印表機狀態...\n")

try:
    r = requests.get(f'http://{IP}:7125/api/printer', timeout=5)
    if r.status_code == 200:
        print(f"  API (7125): ✅ 響應正常")
    else:
        print(f"  API (7125): ⚠️  狀態 {r.status_code}")
except:
    print(f"  API (7125): ❌ 無回應")

# Step 3: Attempt SSH service restart via WebSocket
if ws_ok:
    print(f"\n[3] 嘗試透過 WebSocket 重啟 SSH...\n")

    async def restart_ssh():
        try:
            import websockets
            uri = f"ws://{IP}:{WS_PORT}"

            async with websockets.connect(uri, ping_interval=None, close_timeout=3) as ws:
                # Try various SSH restart commands
                commands = [
                    {"method": "set", "params": {"enable_ssh": 1}},
                    {"method": "restart_sys_service", "params": {"service": "dropbear"}},
                    {"method": "set", "params": {"gcode_cmd": "M200"}},  # Generic command
                ]

                for i, cmd in enumerate(commands):
                    try:
                        await ws.send(json.dumps(cmd))
                        print(f"  [{i+1}] 發送: {cmd['method']}")

                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                            # Print first part of response
                            resp_str = msg if isinstance(msg, str) else str(msg)
                            if len(resp_str) > 50:
                                print(f"      回應: {resp_str[:50]}...")
                        except asyncio.TimeoutError:
                            print(f"      ⏱️  無回應（可能成功）")
                    except Exception as e:
                        print(f"      ❌ {type(e).__name__}")

                return True
        except Exception as e:
            print(f"  ❌ WebSocket 錯誤: {type(e).__name__}: {str(e)[:60]}")
            return False

    try:
        ok = asyncio.run(restart_ssh())
        if ok:
            print(f"\n  ⏳ 等待 SSH 服務啟動 (3 秒)...")
            time.sleep(3)

            # Recheck SSH
            ssh_ok_new = check_port(SSH_PORT)
            if ssh_ok_new and not ssh_ok:
                print(f"  ✅ SSH 現已可用!")
            elif ssh_ok_new:
                print(f"  ✅ SSH 狀態: 正常")
            else:
                print(f"  ❌ SSH 仍無響應")
    except Exception as e:
        print(f"  ❌ 異常: {e}")

# Step 4: Manual recovery steps
if not ssh_ok:
    print(f"\n[4] 建議的手動修復步驟\n")
    print(f"""
  如果 SSH 仍未啟動，請嘗試以下步驟：

  1️⃣  通過 Web UI 重啟印表機
      - 打開瀏覽器訪問: http://{IP}
      - 進入設置 → 系統 → 重啟

  2️⃣  檢查 SSH 設置
      - 設置 → 網絡 → SSH 是否啟用？
      - 如果未啟用，則需要透過 Web UI 手動啟用

  3️⃣  強制重啟
      - 長按印表機電源按鈕 (10 秒)

  4️⃣  檢查防火牆
      - 確認本地網絡未阻擋 SSH port 22
      - 檢查路由器防火牆設置

  5️⃣  檢查 SSH 日誌
      - 透過 Web UI 查看系統日誌
      - 查找任何 SSH 相關的錯誤信息
    """)

# Step 5: Final status
print(f"\n[5] 最終狀態\n")
ssh_final = check_port(SSH_PORT)
print(f"  SSH (22): {'✅ 可用' if ssh_final else '❌ 不可用'}")

if ssh_final:
    print(f"\n✅ K1C 黑已恢復，可以進行檔案下載")
else:
    print(f"\n⚠️  K1C 黑 SSH 仍未啟動，請執行上述手動步驟")

print("\n" + "=" * 70)
