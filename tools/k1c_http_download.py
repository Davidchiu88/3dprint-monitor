#!/usr/bin/env python3
"""K1C file download via HTTP (works during printing)."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
import re
from pathlib import Path

def list_k1c_files(ip: str) -> list:
    """列出 K1C 上的所有 gcode 檔案。"""
    try:
        r = requests.get(f'http://{ip}/downloads/humbnail/', timeout=5)
        # 解析 HTML 中的檔案列表
        items = re.findall(r'href="([^"./][^"]*\.png)"', r.text)
        # 轉換為 gcode 名稱
        gcodes = [item.replace('.png', '.gcode') for item in items]
        return gcodes
    except Exception as e:
        print(f"❌ 列表失敗: {e}")
        return []

def download_k1c_file(ip: str, filename: str, output_dir: str = "downloads") -> bool:
    """從 K1C 下載檔案 (HTTP 方法，列印中可用)。"""
    Path(output_dir).mkdir(exist_ok=True)

    # 嘗試多種可能的路徑
    paths = [
        f'/downloads/original/{filename}',
        f'/downloads/humbnail/{filename}',
        f'/downloads/{filename}',
        f'/gcode/{filename}',
        f'/file/{filename}',
    ]

    for path in paths:
        try:
            url = f'http://{ip}{path}'
            print(f"  嘗試: {path}...", end=' ')

            r = requests.head(url, timeout=3)

            if r.status_code == 200:
                # 開始下載
                r = requests.get(url, timeout=30, stream=True)
                file_path = Path(output_dir) / filename

                size = 0
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        if chunk:
                            f.write(chunk)
                            size += len(chunk)

                print(f"✅ ({size/1024/1024:.1f} MB)")
                return True
            elif r.status_code == 404:
                print(f"❌ 未找到")
            else:
                print(f"⚠️  HTTP {r.status_code}")
        except requests.exceptions.Timeout:
            print(f"⏱️  超時")
        except Exception as e:
            print(f"❌ {type(e).__name__}")

    return False

# ─── 主程式 ────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("K1C HTTP 檔案下載工具（列印中可用）")
    print("=" * 60)

    ips = {
        'K1C 紅': '192.168.0.205',
        'K1C 黑': '192.168.0.92',
    }

    for name, ip in ips.items():
        print(f"\n### {name} ({ip})")

        # 列出檔案
        files = list_k1c_files(ip)
        if not files:
            print("  ❌ 無法獲取檔案列表")
            continue

        print(f"  ✅ 找到 {len(files)} 個檔案")

        # 下載前 3 個檔案
        output_dir = "downloads"
        for fname in files[:3]:
            print(f"\n  下載: {fname}")
            download_k1c_file(ip, fname, output_dir)

    print("\n" + "=" * 60)
    print("下載完成")
    print("=" * 60)
