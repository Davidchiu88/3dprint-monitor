# 樹梅派完整部署指南 🍓

**系統**: Raspberry Pi OS (64-bit)  
**Python**: 3.11+  
**日期**: 2026-06-03

---

## 📋 準備清單

- [ ] 樹梅派 4B/5 (4GB+ RAM)
- [ ] 32GB+ microSD 卡
- [ ] 電源適配器 (3A+)
- [ ] 乙太網線或 WiFi
- [ ] 電腦（用於複製檔案和遠程訪問）

---

## 🚀 自動部署 (推薦)

### **在樹梅派上執行一個命令完成所有設置：**

```bash
# 下載並執行部署腳本
curl https://raw.github.com/[用戶]/3dprint-monitor/main/deploy_raspberry_pi.sh | bash

# 或者 (如果已有本地檔案)
bash deploy_raspberry_pi.sh
```

**這將自動:**
1. ✅ 更新系統
2. ✅ 安裝 Python 3.11
3. ✅ 建立目錄結構
4. ✅ 複製程式碼
5. ✅ 安裝依賴
6. ✅ 配置 Systemd 服務
7. ✅ 設置開機自啟動

**所需時間**: 10-15 分鐘

---

## 🛠️ 手動部署 (分步)

如果自動腳本失敗，按以下步驟手動部署。

### **步驟 1: 初始化樹梅派**

```bash
# 連接到樹梅派 (SSH 或直接)
ssh pi@[樹梅派IP]

# 更新系統
sudo apt update && sudo apt upgrade -y

# 設置基本配置
sudo raspi-config
# 選項:
# - System Options → Hostname (改名為 "printer-monitor")
# - Interface Options → SSH (啟用)
# - Localization (設置時區)
```

### **步驟 2: 安裝 Python**

```bash
# 安裝 Python 3.11 和開發工具
sudo apt install -y python3.11 python3.11-venv python3.11-dev \
    python3-pip build-essential libssl-dev libffi-dev git curl

# 設為預設
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# 驗證
python3 --version
pip3 --version
```

### **步驟 3: 複製程式碼**

#### **方法 A: USB (如果有本地複製)**
```bash
# 掛載 USB
sudo mkdir -p /mnt/usb
sudo mount /dev/sda1 /mnt/usb

# 複製
mkdir -p /home/pi/3dprint
cp -r /mnt/usb/3dprint/* /home/pi/3dprint/

# 卸載
sudo umount /mnt/usb
```

#### **方法 B: Git (推薦)**
```bash
cd /home/pi
git clone https://github.com/[用戶]/3dprint-monitor.git 3dprint
cd 3dprint
```

#### **方法 C: SCP (從電腦)**
```bash
# 在你的 Windows 電腦上
scp -r D:\3dprint pi@[樹梅派IP]:/home/pi/
```

### **步驟 4: 安裝依賴**

```bash
cd /home/pi/3dprint

# 升級 pip
pip3 install --upgrade pip setuptools wheel

# 安裝專案依賴 (可能需要 5-10 分鐘)
pip3 install -r requirements.txt --timeout=1000

# 驗證
python3 -c "import paho, requests, fastapi; print('✅ 依賴已安裝')"
```

### **步驟 5: 配置印表機**

```bash
# 編輯配置檔
nano /home/pi/3dprint/config/printers.yaml

# 修改 IP 地址：
# 1. 按 Ctrl+X 找尋
# 2. 輸入 "192.168"
# 3. 輸入實際 IP 地址
# 4. Ctrl+O 儲存，Ctrl+X 退出
```

**查找 IP 的方法:**
```bash
# 掃描網絡
arp-scan -l

# 或
nmap -sn 192.168.0.0/24

# 或登入路由器查看已連接設備
```

### **步驟 6: 測試運行**

```bash
# 測試監控系統
python3 -m src.main &

# 等待 5 秒，然後在新終端測試 API
curl http://localhost:7000/api/status | python3 -m json.tool

# 如果成功看到 JSON，按 Ctrl+C 停止
```

### **步驟 7: 配置 Systemd 服務**

```bash
# 建立監控系統服務
sudo tee /etc/systemd/system/printer-monitor.service > /dev/null <<'EOF'
[Unit]
Description=3D Printer Monitoring System
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/3dprint
ExecStart=/usr/bin/python3 -m src.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 建立 API 伺服器服務
sudo tee /etc/systemd/system/printer-api.service > /dev/null <<'EOF'
[Unit]
Description=3D Printer API Server
After=printer-monitor.service
Wants=printer-monitor.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/3dprint
ExecStart=/usr/bin/python3 -m uvicorn src.api_server:app --host 0.0.0.0 --port 7000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 啟用和啟動服務
sudo systemctl daemon-reload
sudo systemctl enable printer-monitor.service
sudo systemctl enable printer-api.service
sudo systemctl start printer-monitor.service
sudo systemctl start printer-api.service

# 驗證
sudo systemctl status printer-monitor.service
sudo systemctl status printer-api.service
```

---

## 📱 遠程管理

### **使用 Python 管理工具**

```bash
# 在你的電腦上
pip install paramiko

# 查看狀態
python tools/raspberry_pi_manager.py -H pi@[樹梅派IP] -p [密碼] status

# 查看 API 狀態
python tools/raspberry_pi_manager.py -H pi@[樹梅派IP] -p [密碼] api-status

# 查看日誌
python tools/raspberry_pi_manager.py -H pi@[樹梅派IP] -p [密碼] logs printer-monitor 50

# 重啟服務
python tools/raspberry_pi_manager.py -H pi@[樹梅派IP] -p [密碼] restart-monitor

# 測試印表機
python tools/raspberry_pi_manager.py -H pi@[樹梅派IP] -p [密碼] test-printers

# 下載日誌
python tools/raspberry_pi_manager.py -H pi@[樹梅派IP] -p [密碼] download-log
```

### **使用 SSH 直接管理**

```bash
# 查看系統狀態
ssh pi@[IP] "free -h && df -h"

# 查看溫度
ssh pi@[IP] "vcgencmd measure_temp"

# 查看日誌
ssh pi@[IP] "journalctl -u printer-monitor -f"

# 重啟服務
ssh pi@[IP] "sudo systemctl restart printer-monitor.service"
```

---

## 🌐 訪問 API

### **本地 (在樹梅派上)**
```bash
curl http://localhost:7000/api/status
```

### **區域網 (從其他電腦)**
```bash
# 查看樹梅派 IP
hostname -I

# 訪問 API
curl http://[樹梅派IP]:7000/api/status

# Web 瀏覽器
http://[樹梅派IP]:7000/docs
```

---

## 📊 日誌和監控

### **查看實時日誌**
```bash
# 在樹梅派上
journalctl -u printer-monitor -f

# 或從電腦遠程查看
ssh pi@[IP] "journalctl -u printer-monitor -f"
```

### **查看日誌檔**
```bash
# 路徑: /home/pi/3dprint/printer_monitor.log
tail -f /home/pi/3dprint/printer_monitor.log

# 下載到電腦
scp pi@[IP]:/home/pi/3dprint/printer_monitor.log ./
```

### **監控系統資源**
```bash
# CPU 溫度
vcgencmd measure_temp

# 記憶體
free -h

# 磁盤
df -h

# 進程
top -bn1 | head -20
```

---

## 🔧 故障排除

### **服務無法啟動**

```bash
# 查看詳細日誌
journalctl -u printer-monitor -n 50

# 手動執行測試
cd /home/pi/3dprint
python3 -m src.main

# 檢查依賴
pip3 list | grep -E "paho|requests|fastapi"
```

### **無法連接印表機**

```bash
# 測試網絡連接
ping 192.168.0.30

# 掃描網絡找 IP
arp-scan -l

# 查看日誌中的連接錯誤
journalctl -u printer-monitor | grep -i "error\|timeout"
```

### **API 無響應**

```bash
# 查看 API 伺服器日誌
journalctl -u printer-api -f

# 測試連接
curl http://localhost:7000/api/status

# 檢查 port 是否在使用
sudo lsof -i :7000
```

### **磁盤空間不足**

```bash
# 查看空間
df -h

# 清理舊日誌
sudo rm -f /home/pi/3dprint/printer_monitor.log*

# 清理包管理器緩存
sudo apt clean && sudo apt autoclean

# 查看大檔案
du -sh /home/pi/* | sort -h
```

---

## 🎯 性能優化

### **禁用不需要的服務**

```bash
# 禁用藍牙 (節省 10MB RAM)
sudo systemctl disable bluetooth.service
sudo systemctl stop bluetooth.service

# 禁用 HDMI (如未使用)
sudo hdmi_mode=1
```

編輯 `/boot/firmware/config.txt`:
```bash
sudo nano /boot/firmware/config.txt

# 添加以下行
dtoverlay=disable-bt
dtoverlay=disable-wifi  # (如果使用乙太網)
```

### **監控樹梅派的資源使用**

```bash
# 定期檢查
watch -n 5 'free -h && echo "---" && vcgencmd measure_temp'

# 或建立監控腳本
cat > /home/pi/monitor.sh <<'EOF'
#!/bin/bash
while true; do
    echo "$(date): Temp=$(vcgencmd measure_temp), RAM=$(free -h | grep Mem | awk '{print $3 "/" $2}')"
    sleep 60
done
EOF
chmod +x /home/pi/monitor.sh
```

---

## 📈 系統備份

### **備份配置和資料**

```bash
# 備份到電腦
scp -r pi@[IP]:/home/pi/3dprint/config ./backup/
scp -r pi@[IP]:/home/pi/3dprint/data ./backup/

# 或使用 rsync (增量備份，更快)
rsync -avz pi@[IP]:/home/pi/3dprint/config ./backup/
rsync -avz pi@[IP]:/home/pi/3dprint/data ./backup/
```

### **完整系統備份 (microSD 卡)**

```bash
# 在樹梅派上建立鏡像
sudo dd if=/dev/mmcblk0 of=/mnt/usb/pi-backup.img bs=4M status=progress

# 或使用更快的方法
sudo pv -tpreb /dev/mmcblk0 | gzip > /mnt/usb/pi-backup.img.gz
```

---

## ✅ 部署檢查清單

完成後確認:

- [ ] 樹梅派 OS 已安裝
- [ ] Python 3.11 已安裝
- [ ] 代碼已複製到 /home/pi/3dprint
- [ ] 依賴已安裝 (pip list)
- [ ] 配置檔已編輯 (IP 地址)
- [ ] 手動測試成功
- [ ] Systemd 服務已建立
- [ ] 開機自啟動已驗證
- [ ] API 可訪問 (http://[IP]:7000)
- [ ] 至少一台印表機可連接
- [ ] 日誌無嚴重錯誤

---

## 🚀 下一步

1. **設置遠程訪問** (如需要)
   - 使用 VPN 或 SSH 隧道
   - 設置 DynDNS (動態 DNS)

2. **配置備份**
   - 定期備份配置和資料
   - 自動上傳到雲端

3. **設置告警** (可選)
   - 列印完成通知
   - 錯誤警報

4. **前端 UI** (可選)
   - 安裝 Web 前端
   - 建立儀表板

---

## 📞 支持資源

- **文檔**: 參考本目錄中的其他 .md 檔案
- **日誌**: `journalctl -u printer-monitor -f`
- **遠程管理**: `python tools/raspberry_pi_manager.py -H [IP] -p [密碼] [命令]`
- **SSH**: `ssh pi@[IP]`

---

**部署完成！系統已準備好 24/7 運行。** 🎉
