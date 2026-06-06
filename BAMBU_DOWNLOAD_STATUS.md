# 拓竹 Bambu Lab 檔案下載狀態報告

**日期**: 2026-06-03  
**狀態**: FTP 服務已禁用 ⛔

---

## 🔍 診斷結果

### 當前狀態

| 設備 | MQTT | FTP Port | FTP 服務 | 原因 |
|------|------|----------|---------|------|
| **Bambu A1 Mini** | ✅ 連接 | 🟢 開放 | ❌ 禁用 | 列印中或 LAN 關閉 |
| **Bambu A1** | ✅ 連接 | 🟢 開放 | ❌ 禁用 | 列印中或 LAN 關閉 |
| **Bambu A1 #2** | ✅ 連接 | 🟢 開放 | ❌ 禁用 | 列印中或 LAN 關閉 |

### 診斷訊息

```
FTP 未開放（印表機列印中時自動關閉）
在印表機空閒時切換至 LAN 模式即可啟用
```

---

## 🛠️ 解決方案

### 原因分析

拓竹 (Bambu Lab) 有以下行為：
- **列印中**: FTP 服務自動關閉（為了穩定性）
- **空閒時**: FTP 需要切換至 **LAN 模式** 才能啟用
- **離線**: 無法訪問任何服務

### 步驟 1: 檢查印表機狀態

在拓竹觸屏顯示屏上:
1. 進入 **主界面**
2. 查看當前狀態：
   - 🟢 **空閒** → 可以啟用 FTP
   - 🔴 **列印中** → 等待列印完成

### 步驟 2: 啟用 LAN 模式

**如果印表機空閒:**

在觸屏顯示屏上:
1. 進入 **設置** → **網絡**
2. 切換至 **LAN 模式**（而不是雲端模式）
3. 確認 IP 地址（應該是 192.168.0.xx）
4. 返回主界面

**透過 Web UI:**
1. 打開瀏覽器: `http://192.168.0.30` （根據實際 IP）
2. 進入設置 → 網絡
3. 啟用 LAN 模式

### 步驟 3: 驗證 FTP

```bash
# 執行診斷工具
cd D:\3dprint
python tools/check_bambu_files.py
```

應該看到:
```
Bambu A1 Mini: ✅ [N] files
```

### 步驟 4: 下載檔案

一旦 FTP 啟用，執行:
```bash
# 完整下載器
python tools/bambu_download_full.py

# 或透過 API
python tools/direct_download_test.py
```

檔案將保存到:
```
downloads/Bambu_A1_Mini/
downloads/Bambu_A1/
downloads/Bambu_A1_#2/
```

---

## ⏱️ 自動監控方案

如果想在 FTP 恢復時自動下載，使用監控工具：

```bash
python tools/k1c_monitor_and_download.py
```

或為拓竹建立類似的監控器。

---

## 📊 之前的成功下載

日誌顯示在 2026-06-03 02:21 和 02:28 時成功下載：

```
2026-06-03 02:21:21,142 - Bambu download OK: /cache/3DBenchy by Creative Tool_plate_1.gcode
2026-06-03 02:28:30,578 - Bambu download OK: /cache/?啗?-A1?_45cm.3mf
```

這表明在那些時間段，拓竹的 FTP 是啟用的。

---

## 🔧 故障排除

### 仍無法啟用 FTP

1. **重啟印表機**
   - 完全關閉電源 10 秒
   - 重新開啟
   - 等待 2-3 分鐘啟動

2. **檢查網絡連接**
   ```bash
   ping 192.168.0.30  # 應該回應
   ```

3. **檢查 LAN 模式**
   - 確認已切換至 LAN 模式（不是雲端）
   - 某些型號需要在觸屏菜單中明確啟用

4. **檢查防火牆**
   - 確保 port 990 未被阻擋
   - 嘗試臨時禁用防火牆測試

### 仍然超時

如果即使啟用 LAN 模式仍然超時，可能是：
- 網絡延遲高
- FTP 服務故障
- 印表機固件問題

**解決方案:**
- 嘗試透過 Web UI 下載（如果支援）
- 通過記憶卡物理轉移檔案
- 聯繫官方支援

---

## 📚 相關資源

- [Bambu Lab 官方文檔](https://www.bambulab.com/)
- [LAN 模式說明](https://bambu.wiki/)
- FTP 連接：`bblp / [access_code]` @ port 990

---

## 快速參考

| 操作 | 命令 |
|------|------|
| 檢查檔案列表 | `python tools/check_bambu_files.py` |
| 完整下載 | `python tools/bambu_download_full.py` |
| 診斷連接 | `python tools/fix_k1c_black_ssh.py` （對 Bambu 也有幫助）|

---

**下次測試時間**: 建議在拓竹空閒且切換至 LAN 模式後重試。
