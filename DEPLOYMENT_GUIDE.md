# 3D 印表機監控系統 - 辦公室部署指南

**系統**: 3D 印表機監控和管理系統  
**支援**: Bambu Lab (A1/A1 Mini) 和 Creality K1C  
**環境**: Windows 11

---

## 📋 部署清單

- [ ] Python 3.8+ 已安裝
- [ ] 專案文件複製到辦公室電腦
- [ ] 依賴已安裝
- [ ] 配置檔已更新（IP 地址等）
- [ ] 測試連接
- [ ] 開機自啟動已配置（可選）

---

## 🚀 快速開始

### 1️⃣ 準備環境

**要求:**
- Windows 7+ 或 Windows Server
- Python 3.8+ (推薦 3.10+)
- 可訪問區域網 (192.168.0.x)
- 至少 500 MB 可用空間

**安裝 Python:**
```bash
# 下載: https://www.python.org/downloads/
# 安裝時勾選 "Add Python to PATH"

# 驗證
python --version
pip --version
```

### 2️⃣ 複製專案

將整個 `D:\3dprint` 目錄複製到辦公室電腦：
```
D:\3dprint\           ← 複製此目錄
├── config\
├── data\
├── src\
├── tools\
├── start_server.bat  ← 啟動腳本
├── start_server.ps1
└── ...
```

### 3️⃣ 安裝依賴

```bash
cd D:\3dprint
pip install -r requirements.txt
```

**預期輸出:**
```
Successfully installed paho-mqtt-2.1.0 requests-2.31.0 ...
```

### 4️⃣ 配置印表機

編輯 `config/printers.yaml` 更新 IP 地址：

```yaml
printers:
  - name: "Bambu A1 Mini"
    type: "bambu_lab"
    ip: "192.168.X.X"          # ← 更新為實際 IP
    device_id: "XXXXXXXXXXXXXXX"
    access_code: "XXXXXXXX"

  - name: "Creality K1C 紅"
    type: "creality_k1c"
    ip: "192.168.X.X"          # ← 更新為實際 IP
```

**如何找 IP:**
```bash
# 在 Windows 命令提示字元
arp -a                    # 列出所有網路設備

# 或在路由器設置中查看已連接裝置
```

### 5️⃣ 啟動系統

**方法 A: 雙擊啟動 (推薦 - Windows)**
```
右鍵 start_server.bat → 以系統管理員身份執行
```

**方法 B: PowerShell**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\start_server.ps1
```

**方法 C: 命令行**
```bash
cd D:\3dprint
python -m src.main      # 監控系統

# 另一個終端:
uvicorn src.api_server:app --host 0.0.0.0 --port 7000
```

---

## 🌐 訪問系統

### API 伺服器

- **地址**: `http://[辦公室電腦IP]:7000`
- **API 文檔**: `http://[辦公室電腦IP]:7000/docs`
- **Port**: 7000

**範例:**
```
http://192.168.1.100:7000/api/status
http://192.168.1.100:7000/api/history?limit=10
```

### 本地訪問

在辦公室電腦上:
```
http://localhost:7000
```

### 區域網訪問

從其他電腦訪問:
```
http://[辦公室電腦IP]:7000
```

取得電腦 IP:
```bash
# Windows
ipconfig

# 找 IPv4 位址
```

---

## 🔧 常見操作

### 查看印表機狀態

```bash
# 從任何電腦
curl http://[伺服器IP]:7000/api/status | python -m json.tool
```

### 查看檔案列表

```bash
# Bambu A1 Mini 的檔案
curl http://localhost:7000/api/files/Bambu%20A1%20Mini
```

### 下載檔案

```bash
# K1C 檔案下載
python tools/direct_download_test.py

# Bambu 檔案下載
python tools/bambu_download_full.py
```

### 監控列印進度

```bash
# 自動監控並下載
python tools/k1c_monitor_and_download.py

# 查看日誌
tail -f printer_monitor.log
```

---

## 📊 系統架構

```
┌─────────────────────────────────────────┐
│     3D 印表機監控系統 (辦公室)          │
│          port 7000                      │
├─────────────────────────────────────────┤
│  API 伺服器 (uvicorn)                   │
│  ├── /api/status        (印表機狀態)    │
│  ├── /api/files/[name]  (檔案列表)      │
│  ├── /api/history       (列印歷史)      │
│  └── /api/profiles      (機器配置)      │
├─────────────────────────────────────────┤
│  監控系統 (Bambu + K1C)                 │
│  ├── MQTT 連接 (Bambu)                  │
│  ├── WebSocket (K1C)                    │
│  ├── FTP 管理 (Bambu)                   │
│  └── SSH 管理 (K1C)                     │
├─────────────────────────────────────────┤
│  本地存儲                               │
│  ├── data/printer_status.json           │
│  ├── data/printer_history.jsonl         │
│  └── snapshots/[機器]/[日期]/           │
└─────────────────────────────────────────┘
```

---

## 🐛 故障排除

### 啟動失敗

**問題**: 模組未找到
```
ModuleNotFoundError: No module named 'paho'
```
**解決**:
```bash
pip install -r requirements.txt
```

**問題**: Port 已被使用
```
Error: Unable to bind to port 7000
```
**解決**:
```bash
# 方法1: 使用另一個 port
uvicorn src.api_server:app --port 7001

# 方法2: 找出佔用 port 的進程
netstat -ano | findstr :7000
taskkill /PID [PID] /F
```

### 無法連接印表機

**檢查步驟**:
```bash
# 1. 檢查 IP 連接
ping 192.168.0.30

# 2. 查看配置檔
cat config\printers.yaml

# 3. 查看日誌
Get-Content printer_monitor.log -Tail 20
```

### Bambu FTP 超時

根據之前診斷，FTP 需要：
1. 印表機空閒（不在列印）
2. 切換至 **LAN 模式** (不是雲端)

詳見 `BAMBU_DOWNLOAD_STATUS.md`

### K1C SSH 不可用

詳見 `FIXES_SUMMARY.md` 中的修復步驟

---

## 🔐 安全性

### 本地網絡訪問

- ✅ 區域網 (192.168.x.x) 內可訪問
- ❌ 互聯網上無法直接訪問（需 VPN/遠程連接）

### 建議

1. **防火牆配置**
   - 允許 port 7000 (API)
   - 允許 8883 (MQTT)
   - 允許 9999 (K1C WebSocket)

2. **訪問控制**
   - 僅在信任的網絡上運行
   - 不要暴露到互聯網

3. **遠程訪問** (如需要)
   - 使用 VPN 或 SSH 隧道
   - 或使用 Obico/OctoEverywhere

---

## 📈 監控和日誌

### 日誌位置

```
printer_monitor.log      ← 系統日誌
data/printer_status.json ← 當前狀態
data/printer_history.jsonl ← 歷史記錄
snapshots/               ← 攝像頭截圖
```

### 監控日誌

```bash
# 實時監控
tail -f printer_monitor.log

# 搜索特定錯誤
Select-String "ERROR" printer_monitor.log
```

---

## 🚀 進階設置

### 開機自啟動

**方法1: 任務計劃**
1. 打開 `taskschd.msc`
2. 新建基本工作
3. 觸發器: 啟動時
4. 操作: 執行 `start_server.bat`

**方法2: Startup 資料夾**
```
C:\Users\[用戶]\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\
```
複製快捷方式到此目錄

### 後台服務化

使用 NSSM 或 WinSW:
```bash
# 安裝為服務
nssm install "3D Printer Monitor" python -m src.main
nssm start "3D Printer Monitor"
```

---

## 📞 支援和資源

### 文檔
- `README.md` - 系統概述
- `K1C_RESOURCES.md` - K1C 相關資源
- `BAMBU_DOWNLOAD_STATUS.md` - Bambu 下載診斷
- `FIXES_SUMMARY.md` - 已知問題和修復

### 工具
- `tools/check_k1c_files.py` - K1C 檔案檢查
- `tools/fix_k1c_black_ssh.py` - K1C SSH 診斷
- `tools/bambu_download_full.py` - Bambu 完整下載

### 官方資源
- [Bambu Lab](https://www.bambulab.com/)
- [Creality K1C](https://www.creality.com/)

---

## ✅ 部署檢查表

完成後檢查:

- [ ] Python 已安裝並在 PATH 中
- [ ] 依賴已安裝 (`pip install -r requirements.txt`)
- [ ] 配置檔已更新 (IP 地址等)
- [ ] 監控系統啟動成功
- [ ] API 伺服器可訪問 (http://localhost:7000)
- [ ] 至少一台印表機可連接
- [ ] 日誌檔生成且無嚴重錯誤
- [ ] 檔案列表可查詢
- [ ] 檔案可下載 (K1C/Bambu)

---

**部署日期**: _____________  
**部署人員**: _____________  
**備註**: _____________

---

*最後更新: 2026-06-03*
