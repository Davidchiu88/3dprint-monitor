# K1C 檔案下載資源和方案

## 📋 核心發現

### K1C SSH 在列印中被禁用 ⚠️

根據 Creality 的設計，K1C 在列印時會自動禁用 SSH 以確保系統穩定性。

**時間軸:**
- 列印中: ❌ SSH 不可用
- 列印完成: ✅ SSH 恢復（1-2 分鐘後）

---

## 🔧 解決方案

### 方案 A: 自動監控和下載（推薦）

**工具**: `tools/k1c_monitor_and_download.py`

```bash
# 監控兩台 K1C，自動下載完成的檔案
python tools/k1c_monitor_and_download.py

# 監控特定機器
python tools/k1c_monitor_and_download.py red    # K1C 紅
python tools/k1c_monitor_and_download.py black  # K1C 黑
```

**功能:**
- ✅ 實時監控列印進度
- ✅ 偵測列印完成
- ✅ 自動透過 SSH 下載檔案
- ✅ 保存到本地 `downloads/` 目錄

---

### 方案 B: 等待列印完成後手動下載

**步驟:**
1. 等待 K1C 列印完成（查看設備顯示屏）
2. 執行診斷工具確認 SSH 已恢復：
   ```bash
   python tools/fix_k1c_black_ssh.py
   ```
3. SSH 可用後執行下載：
   ```bash
   python tools/direct_download_test.py
   ```

---

### 方案 C: 使用官方工具

#### [K1C Config Manager](https://github.com/SirSleep/K1C-Config-Manager)

Python GUI 工具，用於:
- 下載 `.cfg` 配置檔
- 管理 Creality Helper Script
- 自動網路掃描

**安裝:**
```bash
git clone https://github.com/SirSleep/K1C-Config-Manager.git
cd K1C-Config-Manager
pip install -r requirements.txt
python main.py
```

#### [Creality Helper Script](https://github.com/Guilouz/Creality-Helper-Script-Wiki)

高級工具集，包含:
- 韌體升級
- 系統配置
- SSH 管理

**安裝 (需要 SSH):**
```bash
ssh root@192.168.0.205
git clone https://github.com/Guilouz/Creality-Helper-Script.git /usr/data/helper-script
```

---

## 📚 重要資源鏈接

### 官方和社群工具

| 工具 | 說明 | 連結 |
|------|------|------|
| **K1C Root Exploit** | 2025 K1C 根訪問工具 | [GitHub Gist](https://gist.github.com/C0DEbrained/c6f508109e34f43a39f4c22e901408dd) |
| **K1C Tools** | K1C 工具集合 | [GitHub](https://github.com/C0DEbrained/Creality-K1C-Tools) |
| **Helper Script** | K1C 系統管理 | [Wiki](https://guilouz.github.io/Creality-Helper-Script-Wiki/) |
| **Config Manager** | K1C 配置管理器 | [GitHub](https://github.com/SirSleep/K1C-Config-Manager) |

### 遠程訪問方案

| 方案 | 說明 | 連結 |
|------|------|------|
| **Obico** | 免費遠程監控 | [指南](https://www.obico.io/blog/remote-access-creality-k1/) |
| **OctoEverywhere** | 免費遠程訪問 | [文章](https://blog.octoeverywhere.com/remote-access-for-the-creality-k1-and-k1-max/) |

### 文檔和指南

| 資源 | 說明 | 連結 |
|------|------|------|
| **OrcaSlicer 支持** | K1/K1C 列印支持 | [Issue #2103](https://github.com/OrcaSlicer/OrcaSlicer/issues/2103) |
| **Root 教程** | 如何 Root K1C | [指南](https://3dpadvisor.com/blog/how-to-root-creality-k1c/) |
| **Setup 指南** | SimplyPrint 設置 | [指南](https://simplyprint.io/setup-guide/creality/k1c) |

---

## 🔍 K1C API 信息

### 主要端點

```
HTTP:      http://[IP]:7125/api/printer       # API 伺服器
WebSocket: ws://[IP]:9999                    # 實時通信
SSH:       [IP]:22 (root/creality_2023)      # SSH (列印時禁用)
```

### 檔案位置

```
/usr/data/printer_data/gcodes/     # G-code 檔案
/usr/data/printer_data/config/     # 配置檔
/usr/data/printer_data/logs/       # 系統日誌
```

### API 命令範例

**獲取列印機狀態:**
```bash
curl http://192.168.0.205:7125/api/printer
```

**透過 WebSocket 啟動列印:**
```json
{
  "method": "set",
  "params": {
    "opGcodeFile": "printprt:/usr/data/printer_data/gcodes/[filename].gcode"
  }
}
```

---

## ⚡ 快速參考

### 檔案列表查詢

```bash
# K1C 紅
curl 'http://192.168.0.205/downloads/humbnail/' | grep -oP '(?<=href=")[^"]*\.gcode'

# K1C 黑
curl 'http://192.168.0.92/downloads/humbnail/' | grep -oP '(?<=href=")[^"]*\.gcode'
```

### SSH 下載 (當列印完成時)

```bash
# 連接到 K1C
ssh root@192.168.0.205

# 列表檔案
ls /usr/data/printer_data/gcodes/

# 下載檔案
scp root@192.168.0.205:/usr/data/printer_data/gcodes/[filename].gcode ./
```

### 檢查列印進度

```bash
# 不斷刷新狀態
watch -n 5 'curl -s http://192.168.0.205:7125/api/printer | jq ".print_job | {state, print_progress, filename}"'
```

---

## 🚀 推薦流程

### 完整檔案下載流程

```
1. 開始列印 (K1C 自動禁用 SSH)
   ↓
2. 執行監控工具
   python tools/k1c_monitor_and_download.py
   ↓
3. 等待列印完成 (監控工具會自動檢測)
   ↓
4. SSH 自動恢復 (約 1-2 分鐘)
   ↓
5. 檔案自動下載到 downloads/
   ✅ 完成
```

---

## 📝 故障排除

### SSH 連接失敗

```bash
# 檢查 SSH 是否可用
ssh root@192.168.0.205

# 如果失敗，運行診斷工具
python tools/fix_k1c_black_ssh.py

# 檢查是否在列印中
curl -s http://192.168.0.205:7125/api/printer | jq ".print_job.state"
```

### 檔案無法下載

```bash
# 確認 SSH 已恢復
python tools/check_k1c_files.py

# 確認檔案存在
ssh root@192.168.0.205 "ls -la /usr/data/printer_data/gcodes/"

# 手動下載單個檔案
scp root@192.168.0.205:/usr/data/printer_data/gcodes/[filename].gcode ./
```

### 列印中無法訪問

這是正常行為！等待列印完成即可。

---

## 📞 獲取幫助

- **官方文檔**: [Creality 官方](https://www.creality.com/)
- **GitHub Issues**: 各工具的 GitHub 倉庫
- **社群論壇**: GBAtemp、Reddit r/3Dprinting

---

**最後更新**: 2026-06-03
