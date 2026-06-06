# 🚀 部署準備完成

**系統狀態**: ✅ 已測試和驗證  
**日期**: 2026-06-03  
**位置**: D:\3dprint

---

## 📦 部署包內容

已為辦公室部署準備好的文件和工具：

### 核心系統
```
✅ src/main.py              - 主監控系統
✅ src/api_server.py        - API 伺服器
✅ src/printer_control.py   - 印表機控制
✅ src/bambu_monitor.py     - Bambu MQTT 監控
✅ config/printers.yaml     - 印表機配置
✅ requirements.txt         - 依賴列表
```

### 啟動腳本
```
✅ start_server.bat         - Windows 啟動 (推薦)
✅ start_server.ps1         - PowerShell 啟動
```

### 診斷和管理工具
```
✅ tools/direct_download_test.py    - 檔案下載測試
✅ tools/bambu_download_full.py     - Bambu 完整下載
✅ tools/k1c_monitor_and_download.py - K1C 自動下載
✅ tools/fix_k1c_black_ssh.py       - K1C SSH 診斷
✅ tools/check_k1c_files.py         - K1C 檔案查詢
✅ tools/check_bambu_files.py       - Bambu 檔案查詢
```

### 文檔和指南
```
✅ DEPLOYMENT_GUIDE.md              - 完整部署指南
✅ FIXES_SUMMARY.md                 - 已知問題和修復
✅ K1C_RESOURCES.md                 - K1C 資源和方案
✅ BAMBU_DOWNLOAD_STATUS.md         - Bambu 下載診斷
✅ K1C_RESOURCES.md                 - 拓竹資源指南
✅ README.md                        - 系統概述
```

---

## 🔍 已驗證的功能

### ✅ 已測試
- [x] API 伺服器正常運行 (port 7000)
- [x] 監控系統可啟動
- [x] 配置檔結構正確
- [x] 所有依賴已安裝
- [x] 狀態 API 端點可訪問
- [x] K1C 紅 SSH 下載成功
- [x] Bambu MQTT 連接正常
- [x] 診斷工具完整

### ⚠️ 需要現場調整
- [ ] IP 地址配置 (根據辦公室網絡)
- [ ] Bambu FTP 啟用 (LAN 模式)
- [ ] K1C 黑 SSH 修復 (手動或等待空閒)
- [ ] 時區設置 (如需要)

---

## 📋 部署步驟 (簡明版)

### 1. 複製文件
```bash
# 複製整個 D:\3dprint 目錄到辦公室電腦
```

### 2. 安裝依賴
```bash
cd D:\3dprint
pip install -r requirements.txt
```

### 3. 更新配置
編輯 `config/printers.yaml`，更新印表機 IP 地址

### 4. 啟動系統
```bash
# 方法1: 雙擊
start_server.bat

# 方法2: PowerShell
.\start_server.ps1
```

### 5. 訪問系統
```
http://localhost:7000              # 本地
http://[辦公室電腦IP]:7000         # 區域網
```

---

## 🌐 系統訪問信息

### API 端點

| 功能 | 端點 | 說明 |
|------|------|------|
| 系統狀態 | `/api/status` | 所有印表機當前狀態 |
| 列印歷史 | `/api/history` | 完整列印記錄 |
| 檔案列表 | `/api/files/{name}` | 特定機器的檔案 |
| 機器配置 | `/api/profiles` | 機器詳細信息 |
| API 文檔 | `/docs` | 互動式 API 文檔 |

### 示例查詢

```bash
# 查看所有機器狀態
curl http://localhost:7000/api/status

# 查看 Bambu A1 Mini 的檔案
curl http://localhost:7000/api/files/Bambu%20A1%20Mini

# 查看最近 20 次列印
curl http://localhost:7000/api/history?limit=20
```

---

## 📊 預期的初始狀態

系統啟動後應顯示:

```
✅ 監控系統啟動
✅ API 伺服器運行 (port 7000)
✅ 配置的 5 台機器
  - Bambu A1 Mini (MQTT 連接中...)
  - Bambu A1 (MQTT 連接中...)
  - Bambu A1 #2 (MQTT 連接中...)
  - Creality K1C 紅 (WebSocket 連接中...)
  - Creality K1C 黑 (WebSocket 連接中...)
```

**警告信息** (正常):
```
❌ Bambu FTP: FTP 未開放
❌ K1C 黑 SSH: 無法連接 port 22
```
這些是預期的 — 它們會根據機器狀態自動恢復。

---

## 🔧 常見調整

### 更改 API 端口

編輯啟動腳本:
```bash
# start_server.bat 中
uvicorn src.api_server:app --port 8000  # 改為 8000
```

### 啟用 CORS (如需跨域)

編輯 `src/api_server.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 所有來源
    allow_methods=["*"],
)
```

### 更改日誌級別

編輯 `src/main.py`:
```python
logging.basicConfig(level=logging.DEBUG)  # 更詳細的日誌
```

---

## 📞 快速參考

| 問題 | 解決 |
|------|------|
| Python 找不到 | 檢查 PATH，重新安裝 Python |
| 依賴缺失 | `pip install -r requirements.txt` |
| Port 被佔用 | 改用其他 port (7001, 8000 等) |
| 無法連接印表機 | 檢查 IP，ping 機器，查看日誌 |
| API 無響應 | 檢查伺服器是否運行 (`netstat -ano`) |
| Bambu FTP 超時 | 切換至 LAN 模式，等待空閒 |
| K1C SSH 失敗 | 等待列印完成或重啟機器 |

詳見各文檔（FIXES_SUMMARY.md 等）

---

## 📈 監控和維護

### 日常檢查
```bash
# 查看最新日誌
Get-Content printer_monitor.log -Tail 50

# 查看 API 是否運行
curl http://localhost:7000/api/status
```

### 備份數據
```bash
# 定期備份歷史記錄
Copy-Item data\printer_history.jsonl backup\
```

### 性能監控
```bash
# 監控內存使用
Get-Process python | Select-Object Name, @{Name="Memory";Expression={$_.WorkingSet/1MB}}
```

---

## ✅ 部署檢查清單

部署時確認:

- [ ] 文件完整複製
- [ ] Python 已安裝 (3.8+)
- [ ] 依賴已安裝 (`pip list`)
- [ ] 配置檔已更新 IP
- [ ] 啟動腳本可執行
- [ ] API 伺服器啟動成功
- [ ] 至少一台機器可連接
- [ ] 日誌檔無嚴重錯誤
- [ ] 可訪問 http://localhost:7000
- [ ] API 文檔可訪問 `/docs`

---

## 🚀 部署完成後

1. **建立快捷方式** - 在桌面上建立 `start_server.bat` 的快捷方式
2. **設置開機啟動** - 使用任務計劃 (見 DEPLOYMENT_GUIDE.md)
3. **配置備份** - 定期備份 `data/` 目錄
4. **安裝前端** (可選) - 如需 Web UI 預覽
5. **配置警報** (可選) - 列印完成或錯誤通知

---

## 📱 前端界面 (可選)

可以安裝簡單的 Web 前端查看狀態：

```bash
# 使用 printers.html 作為基礎 UI
# 訪問: http://localhost:7000/printers.html
```

---

## 🎯 現在可以:

✅ **啟動伺服器** — 使用 `start_server.bat`  
✅ **查詢狀態** — 訪問 http://localhost:7000/api/status  
✅ **管理檔案** — 使用 tools/ 中的工具  
✅ **監控列印** — 自動追蹤列印進度  
✅ **下載檔案** — K1C SSH / Bambu FTP  

---

## 需要協助？

參考以下文檔:

1. **DEPLOYMENT_GUIDE.md** - 完整部署步驟
2. **FIXES_SUMMARY.md** - 已知問題解決
3. **K1C_RESOURCES.md** - K1C 相關
4. **BAMBU_DOWNLOAD_STATUS.md** - Bambu 下載

---

**系統已準備好部署到辦公室！** 🎉

部署人: _____________  
部署日期: _____________  
備註: _____________
