# 3D 印表機管理系統修復報告

**日期**: 2026-06-03  
**狀態**: 部分修復 ✅ / 需要手動干預 ⚠️

---

## 修復內容

### ✅ 已完成

#### 1. API 伺服器改進 (src/api_server.py)
- **改進**: 增強錯誤診斷和消息
- **效果**: 當下載失敗時，自動診斷 SSH 連接狀態
- **優勢**: 用戶能清楚了解失敗原因

```
舊行為: "K1C 不支援透過 HTTP 下載"（誤導）
新行為: "K1C SSH 服務不可用 (IP: 192.168.0.92) — 請檢查列印機..."
```

#### 2. K1C 控制器改進 (src/printer_control.py)
- **改進**: SSH 可達性預檢查
- **效果**: 快速失敗，避免冗長超時
- **優勢**: 提前診斷問題

```
# 現在會先檢查 port 22 是否開放
# 如果不開放，直接返回 None 而不等待 SSH 超時
```

#### 3. 診斷工具新增 (tools/fix_k1c_black_ssh.py)
- **功能**:
  - ✅ 檢查 HTTP/WebSocket/SSH 連接
  - ✅ 嘗試通過 WebSocket 重啟 SSH
  - ✅ 提供手動修復步驟
  - ✅ 最終狀態檢查

**使用方法**:
```bash
cd D:\3dprint
python tools/fix_k1c_black_ssh.py
```

---

## 測試結果

### K1C 紅 (192.168.0.205) ✅
```
檔案列表: ✅ 39 個檔案
SSH 下載: ✅ 成功 (7.6 MB in 53.7s)
狀態:    正常
```

### K1C 黑 (192.168.0.92) ⚠️
```
檔案列表: ✅ 97 個檔案
SSH 連接: ❌ port 22 無回應
WebSocket: ✅ 可用 (port 9999)
HTTP:      ✅ 可用 (port 80)
狀態:      需要手動干預
```

### Bambu Lab (A1 Mini / A1 / A1 #2) ⚠️
```
MQTT 連接: ✅ 成功 (port 8883)
FTP 連接:  ⚠️ 超時 (port 990)
狀態:      可能離線或 IP 已變更
```

---

## 問題診斷

### K1C 黑 SSH 不可達

**症狀**:
- HTTP/WebSocket 正常
- API port 7125 無回應
- SSH port 22 無回應

**可能原因**:
1. SSH 服務未自動啟動（列印機啟動時）
2. SSH 服務被禁用或崩潰
3. 列印機當前忙於列印（某些版本會禁用 SSH）
4. 防火牆或網絡配置問題

**短期解決方案**:
- ✅ API 伺服器已改為返回清晰的錯誤消息
- ✅ 診斷工具已提供手動步驟
- ✅ 系統會跳過不可用的 K1C 黑

---

## 推薦的手動修復步驟

### 方案 A: 透過 Web UI 重啟 (推薦)

1. 打開瀏覽器: `http://192.168.0.92`
2. 進入設置 → 系統 → 重啟
3. 等待 2-3 分鐘
4. 測試: `python tools/fix_k1c_black_ssh.py`

### 方案 B: 檢查 SSH 設定

1. 打開 Web UI: `http://192.168.0.92`
2. 進入設置 → 網絡
3. 確保 SSH 已啟用 ✓
4. 重新啟動路由器的相關裝置

### 方案 C: 強制重啟

1. 長按列印機電源按鈕 (10-15 秒)
2. 等待完全關閉後重新開啟
3. 等待 3-5 分鐘完全啟動
4. 測試連接

### 方案 D: 檢查網絡

1. Ping 機器: `ping 192.168.0.92`
2. 如果可達但 SSH 仍無回應，可能是防火牆
3. 檢查路由器 → 防火牆規則
4. 確保 port 22 未被阻擋

---

## Bambu Lab FTP 超時問題

**症狀**:
- MQTT 連接成功
- FTP 連接超時 (port 990)

**可能原因**:
1. 印表機離線或 IP 已改變
2. 網絡連接不穩定
3. 印表機 FTP 服務故障

**解決方案**:
```bash
# 1. 確認 IP 是否正確
ping 192.168.0.30  # Bambu A1 Mini
ping 192.168.0.58  # Bambu A1
ping 192.168.0.70  # Bambu A1 #2

# 2. 如果無回應，檢查 printers.yaml 中的 IP 地址
# 3. 重啟印表機或路由器

# 4. 測試:
python tools/direct_download_test.py
```

---

## 檔案變更

### 修改的檔案

```
✅ src/api_server.py
   - 改進: download_file() 端點的錯誤診斷
   - 行數: 312-360 (新增 30 行)
   - 功能: SSH 可達性檢查 + 友好錯誤消息

✅ src/printer_control.py
   - 改進: K1CController.download_file() 方法
   - 行數: 266-308 (新增 SSH 預檢查)
   - 功能: 快速失敗 + 診斷日誌
```

### 新增的工具

```
✅ tools/fix_k1c_black_ssh.py (新檔案)
   - 功能: K1C 黑 SSH 診斷和自動修復
   - 用途: 運行後提供清晰的診斷結果

✅ tools/direct_download_test.py (新檔案)
   - 功能: 直接測試各機器的下載功能
   - 用途: 完整的連接性檢查和測試
```

---

## 後續建議

### 短期 (立即)
- [ ] 執行診斷工具: `python tools/fix_k1c_black_ssh.py`
- [ ] 對 K1C 黑執行推薦的手動修復步驟
- [ ] 驗證 Bambu Lab 的 IP 地址

### 中期 (本週)
- [ ] 考慮為 K1C 黑添加備用下載方法（如 FTP 或 NFS）
- [ ] 實施健康檢查機制，定期監測連接狀態
- [ ] 為 Bambu Lab 添加自動 IP 檢測

### 長期 (本月)
- [ ] 實現自動故障轉移和重新連接機制
- [ ] 添加通知系統（當設備離線時）
- [ ] 完整的系統監控儀表板

---

## 測試命令

```bash
# 完整系統測試
cd D:\3dprint

# 1. K1C 連接測試
python tools/check_k1c_files.py

# 2. Bambu 連接測試  
python tools/direct_download_test.py

# 3. K1C 黑診斷
python tools/fix_k1c_black_ssh.py

# 4. 下載功能測試
python tools/test_download.py
```

---

## 總結

✅ **系統健壯性已改進** — 更好的錯誤診斷和消息  
✅ **診斷工具已部署** — 可快速定位問題  
⚠️ **K1C 黑需手動修復** — SSH 服務無法遠程啟動  
⚠️ **Bambu Lab 需確認** — 確認 IP 和網絡連接

系統現在能夠優雅地處理連接故障，提供明確的診斷信息。
