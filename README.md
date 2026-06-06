# 3D Printer Status Monitoring System

監控家庭網絡中的 3D 印表機（Creality K1C 和 Bambu Lab A1/A1 Mini），即時跟踪列印進度、溫度和狀態。

## 功能特性

- 🖨️ **多品牌支持**: Creality K1C (REST API) 和 Bambu Lab (MQTT)
- 📊 **即時監控**: 自動更新列印進度、溫度、狀態
- 💾 **數據持久化**: 保存當前狀態和歷史記錄
- 🔔 **易於擴展**: 為 Telegram 和其他通知系統做好準備
- 🛡️ **本地優先**: 所有通信都在局域網進行，無需互聯網

## 支持的指標

### 通用指標
- 列印進度 (%)
- 噴嘴溫度 (當前/目標)
- 熱床溫度 (當前/目標)
- 列印狀態 (進行中/暫停/閒置/錯誤)
- 當前檔案名
- 剩餘時間

### 特定品牌
**Bambu Lab:**
- AMS 耗材信息
- 濕度監控
- 攝像頭狀態

**Creality K1C:**
- 風扇速度
- 運動系統狀態

## 安裝

1. **克隆/下載項目**:
   ```bash
   cd D:\3Dprint
   ```

2. **安裝依賴**:
   ```bash
   pip install -r requirements.txt
   ```

3. **配置打印機**:
   - 編輯 `config/printers.yaml`
   - 填入各打印機的 IP 地址、設備 ID 和訪問碼
   
   **獲取 Bambu Lab 訪問碼**:
   - 在打印機屏幕上: 設置 → 網絡 → 訪問碼
   - 或在 Bambu Lab 官方應用設置中找到

   **獲取 Creality K1C IP**:
   - 在打印機屏幕上查看 Wi-Fi 設置

## 使用

### 啟動監控系統
```bash
python -m src.main
```

系統將：
- 連接到所有已配置的打印機
- 實時顯示狀態
- 每 30 秒更新一次 Creality 打印機狀態
- 將所有數據保存到 JSON 文件

### 輸出文件

- **data/printer_status.json** - 當前所有打印機的狀態
- **data/printer_history.jsonl** - 歷史狀態記錄（每行一個 JSON）
- **printer_monitor.log** - 系統日誌

## 架構

```
PrinterMonitoringSystem (主協調器)
├── BambuLabMonitor (MQTT 客戶端)
│   ├── Bambu A1
│   └── Bambu A1 Mini
├── CrealityK1CMonitor (REST API 客戶端)
│   ├── Creality K1C #1
│   └── Creality K1C #2
└── DataStore (數據持久化)
    ├── printer_status.json
    └── printer_history.jsonl
```

## 技術細節

### Bambu Lab (MQTT)
- 協議: MQTT over TLS (port 8883)
- 認證: 用戶名 `bblp`，密碼為訪問碼
- 主題: `device/{device_id}/report`
- 實時更新: MQTT 消息觸發狀態更新

### Creality K1C (HTTP REST)
- 協議: HTTP (port 7125)
- API 端點: `/api/printer`
- 輪詢間隔: 30 秒
- 無認證: 本地網絡訪問

## 下一步 (Telegram 集成)

計劃在後續版本中添加：
- 定期狀態推送到 Telegram
- 列印完成/失敗通知
- 溫度異常警報
- 通過 Telegram 命令查詢狀態
- 與 Claude Claw Bot 集成

## 故障排除

### 無法連接到 Bambu Lab
- 檢查 IP 地址是否正確
- 確認訪問碼正確
- 檢查防火牆允許 8883 端口
- 查看日誌文件: `printer_monitor.log`

### 無法連接到 Creality K1C
- 檢查 IP 地址是否正確
- 確認打印機已連接到 Wi-Fi
- 檢查防火牆允許 7125 端口
- 嘗試在瀏覽器中訪問 `http://{IP}:7125/api/printer`

### 狀態不更新
- 檢查打印機是否仍在線
- 檢查網絡連接
- 查看日誌中的錯誤信息
- 重啟系統: Ctrl+C 然後重新運行

## 日誌位置
- 實時輸出: 控制台
- 持久日誌: `printer_monitor.log`
- 數據: `data/` 目錄

## 許可證

MIT License

## 反饋

如有問題或建議，請檢查日誌文件和配置設置。
