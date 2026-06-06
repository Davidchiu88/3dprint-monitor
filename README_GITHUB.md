# 3D 印表機監控系統

監控和管理 Bambu Lab 和 Creality K1C 3D 印表機。支持 Windows 和 Raspberry Pi 部署。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)

## ✨ 功能

- 📊 **即時監控** — 列印進度、溫度、狀態
- 🖨️ **多品牌支持** — Bambu Lab (MQTT) / Creality K1C (WebSocket + SSH)
- 📁 **檔案管理** — 列表、下載、刪除 gcode 檔案
- 🔍 **Web API** — RESTful API + 互動式文檔
- 📷 **攝像頭** — 自動拍攝和存儲快照
- 📈 **歷史記錄** — 保存所有列印數據
- ⚡ **低功耗** — Raspberry Pi 24/7 運行
- 🛠️ **易部署** — 自動化部署腳本

## 🖥️ 系統要求

### Windows
- Python 3.8+
- 500MB 存儲空間
- 區域網訪問

### Raspberry Pi
- Pi 4B+ (4GB RAM 推薦)
- 32GB microSD 卡
- Raspberry Pi OS (64-bit)

## 🚀 快速開始

### Windows 部署

```bash
# 1. 複製代碼
git clone https://github.com/[user]/3dprint-monitor.git
cd 3dprint-monitor

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 配置印表機
編輯 config/printers.yaml，修改 IP 地址

# 4. 啟動系統
# 雙擊 start_server.bat
# 或執行:
python -m src.main          # 監控系統 (終端1)
uvicorn src.api_server:app --port 7000  # API 伺服器 (終端2)
```

### Raspberry Pi 部署

```bash
# 一行命令完成部署
cd /home/pi
git clone https://github.com/[user]/3dprint-monitor.git 3dprint
cd 3dprint
bash deploy_raspberry_pi.sh
```

## 📖 文檔

- [Windows 部署指南](./DEPLOYMENT_GUIDE.md)
- [Raspberry Pi 部署指南](./RASPBERRY_PI_SETUP.md)
- [K1C 資源和方案](./K1C_RESOURCES.md)
- [已知問題和修復](./FIXES_SUMMARY.md)
- [Bambu 下載診斷](./BAMBU_DOWNLOAD_STATUS.md)

## 🌐 API 使用

### 查看所有機器狀態

```bash
curl http://localhost:7000/api/status
```

**回應:**
```json
{
  "ok": true,
  "printers": {
    "Bambu A1 Mini": {
      "name": "Bambu A1 Mini",
      "online": true,
      "progress": 45,
      "temp_nozzle": 250,
      "state": "PRINTING"
    }
  }
}
```

### 查詢特定機器的檔案

```bash
curl http://localhost:7000/api/files/Bambu%20A1%20Mini
```

### 查看列印歷史

```bash
curl http://localhost:7000/api/history?limit=20
```

### 互動式 API 文檔

```
http://localhost:7000/docs
```

## 🛠️ 工具和診斷

```bash
# 檢查 K1C 檔案
python tools/check_k1c_files.py

# K1C SSH 診斷
python tools/fix_k1c_black_ssh.py

# Bambu 完整下載
python tools/bambu_download_full.py

# K1C 自動監控和下載
python tools/k1c_monitor_and_download.py

# 樹梅派遠程管理 (從 Windows)
python tools/raspberry_pi_manager.py -H pi@[IP] -p [密碼] status
python tools/raspberry_pi_manager.py -H pi@[IP] -p [密碼] logs printer-monitor 50
python tools/raspberry_pi_manager.py -H pi@[IP] -p [密碼] test-printers
```

## 📊 架構

```
API 伺服器 (port 7000)
    ↑
    ├── 監控系統
    │   ├── Bambu Monitor (MQTT)
    │   ├── K1C Monitor (WebSocket)
    │   └── Data Store
    │
    └── 控制系統
        ├── Bambu Controller (FTP)
        └── K1C Controller (SSH)

本地存儲
├── printer_status.json
├── printer_history.jsonl
└── snapshots/
```

## 🔧 配置

編輯 `config/printers.yaml`:

```yaml
printers:
  - name: "Bambu A1 Mini"
    type: "bambu_lab"
    ip: "192.168.0.30"
    device_id: "XXXXXXXXXXXXXXX"
    access_code: "XXXXXXXX"

  - name: "Creality K1C"
    type: "creality_k1c"
    ip: "192.168.0.205"
```

## 📱 遠程管理

### Raspberry Pi 上查看日誌

```bash
journalctl -u printer-monitor -f
```

### 從 Windows 遠程管理

```bash
# 查看狀態
python tools/raspberry_pi_manager.py -H pi@192.168.1.100 -p password status

# 重啟服務
python tools/raspberry_pi_manager.py -H pi@192.168.1.100 -p password restart-monitor

# 下載日誌
python tools/raspberry_pi_manager.py -H pi@192.168.1.100 -p password download-log
```

## 🐛 故障排除

### 無法連接印表機

1. 檢查 IP 地址是否正確
2. 確認印表機在線
3. 查看日誌:
   ```bash
   # Windows
   Get-Content printer_monitor.log -Tail 20
   
   # Raspberry Pi
   journalctl -u printer-monitor -f
   ```

### Bambu FTP 超時

根據診斷，Bambu FTP 需要：
- 印表機空閒 (不在列印)
- 切換至 **LAN 模式**（而不是雲端）

詳見 [BAMBU_DOWNLOAD_STATUS.md](./BAMBU_DOWNLOAD_STATUS.md)

### K1C SSH 不可用

通常在列印中或需要重啟。詳見 [FIXES_SUMMARY.md](./FIXES_SUMMARY.md)

## 📈 性能

| 指標 | Windows | Raspberry Pi |
|------|---------|--------------|
| **啟動時間** | 2-5 分鐘 | 30 秒 |
| **CPU 使用** | <10% | 5-15% |
| **記憶體使用** | 200-400 MB | 200-300 MB |
| **功耗** | 30-50W | 2-5W |
| **月電費** | ~$10 | ~$0.5 |

## 📄 授權

MIT License - 詳見 [LICENSE](./LICENSE)

## 🤝 貢獻

歡迎提交 Issues 和 Pull Requests!

## 📞 支援

- 📖 查看文檔
- 🔍 檢查日誌
- 📧 提交 Issue

## 🗓️ 更新日誌

### v1.0.0 (2026-06-03)
- ✅ 初始發布
- ✅ Bambu Lab 和 K1C 支援
- ✅ Windows 和 Raspberry Pi 部署
- ✅ Web API 和互動式文檔
- ✅ 遠程管理工具

---

**Made with ❤️ for 3D Printing Enthusiasts**
