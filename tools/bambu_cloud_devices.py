#!/usr/bin/env python3
"""
Bambu Lab Cloud API - 取得帳號下所有設備的 device_id / serial number
支援國際版 (bambulab.com) 和陸版 (bambulab.cn)

用法:
  python tools/bambu_cloud_devices.py
  然後輸入 Bambu 帳號和密碼
"""
import sys, json, getpass
import requests
sys.stdout.reconfigure(encoding='utf-8')

# API endpoints
ENDPOINTS = {
    "international": {
        "login":   "https://api.bambulab.com/v1/user-service/user/login",
        "devices": "https://api.bambulab.com/v1/iot-service/api/user/bind",
        "mqtt":    "us.mqtt.bambulab.com",
    },
    "china": {
        "login":   "https://api.bambulab.cn/v1/user-service/user/login",
        "devices": "https://api.bambulab.cn/v1/iot-service/api/user/bind",
        "mqtt":    "cn.mqtt.bambulab.com",
    },
}

def login(email: str, password: str, region: str = "international") -> dict:
    """Login to Bambu Cloud and return token info."""
    ep = ENDPOINTS[region]
    resp = requests.post(ep["login"], json={
        "account":  email,
        "password": password,
    }, timeout=10)
    data = resp.json()
    if not data.get("success") and resp.status_code != 200:
        # Try with verification code flow or different format
        raise ValueError(f"Login failed: {data.get('message', resp.status_code)}")
    token    = data.get("accessToken") or data.get("token") or data.get("access_token")
    user_id  = data.get("uid") or data.get("userId") or data.get("user_id")
    if not token:
        raise ValueError(f"No access token in response: {list(data.keys())}")
    return {"token": token, "user_id": user_id, "region": region}


def get_devices(token: str, region: str = "international") -> list:
    """Fetch device list from Bambu Cloud."""
    ep = ENDPOINTS[region]
    resp = requests.get(
        ep["devices"],
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    data = resp.json()
    devices = data.get("devices") or data.get("data") or []
    return devices


def main():
    print("=" * 55)
    print(" Bambu Cloud - 取得設備序號 (Device ID)")
    print("=" * 55)
    print()

    print("版本選擇:")
    print("  1. 國際版 (bambulab.com)")
    print("  2. 陸版 (bambulab.cn)")
    choice = input("輸入 1 或 2 (預設 1): ").strip() or "1"
    region = "china" if choice == "2" else "international"

    email    = input("Bambu 帳號 (Email): ").strip()
    password = getpass.getpass("密碼: ")

    print("\n登入中...")
    try:
        auth = login(email, password, region)
        print(f"登入成功！")
    except Exception as e:
        print(f"登入失敗: {e}")
        print("\n如果遇到驗證碼問題，請到 Bambu Studio 或 Handy App 先登入一次")
        return

    print("\n取得設備列表...")
    try:
        devices = get_devices(auth["token"], region)
    except Exception as e:
        print(f"取得設備失敗: {e}")
        return

    if not devices:
        print("沒有找到任何設備")
        return

    print(f"\n找到 {len(devices)} 台設備：")
    print("-" * 55)

    yaml_lines = []
    for d in devices:
        name    = d.get("name") or d.get("dev_name") or "Unknown"
        dev_id  = d.get("dev_id") or d.get("serial") or d.get("device_id") or "?"
        model   = d.get("dev_model_name") or d.get("model") or "?"
        ip_info = d.get("nozzle_diameter") or ""

        print(f"  名稱:   {name}")
        print(f"  型號:   {model}")
        print(f"  序號:   {dev_id}  ← 這是 device_id")
        print(f"  原始資料: {json.dumps({k:v for k,v in d.items() if k in ('dev_id','name','dev_model_name','nozzle_diameter','task_id')}, ensure_ascii=False)}")
        print()

        yaml_lines.append(f'  # {name} ({model})')
        yaml_lines.append(f'  - name: "{name}"')
        yaml_lines.append(f'    type: "bambu_lab"')
        yaml_lines.append(f'    ip: "FILL_IN_IP"')
        yaml_lines.append(f'    device_id: "{dev_id}"')
        yaml_lines.append(f'    access_code: "FILL_IN_ACCESS_CODE"')
        yaml_lines.append("")

    print("-" * 55)
    print("\nYAML 設定（複製到 config/printers.yaml）：")
    print("\n".join(yaml_lines))

    # Save token for cloud MQTT use
    token_file = "data/bambu_cloud_token.json"
    import json as _json
    from pathlib import Path
    Path("data").mkdir(exist_ok=True)
    _json.dump({
        "token": auth["token"],
        "user_id": auth["user_id"],
        "region": region,
        "mqtt_host": ENDPOINTS[region]["mqtt"],
    }, open(token_file, "w", encoding="utf-8"), indent=2)
    print(f"\n✓ Token 已儲存到 {token_file}（可用於雲端 MQTT 模式）")


if __name__ == "__main__":
    main()
