#!/bin/bash
# 樹梅派自動部署腳本
# 使用: curl https://[URL]/deploy_raspberry_pi.sh | bash
# 或: bash deploy_raspberry_pi.sh

set -e  # 錯誤時停止

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# 配置
INSTALL_PATH="/home/pi/3dprint"
PYTHON_VERSION="python3.11"
USER="pi"
PORT=7000

echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  3D 印表機監控系統 - 樹梅派部署       ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""

# 檢查是否在樹梅派上運行
if ! grep -q "Raspberry" /proc/device-tree/model 2>/dev/null; then
    echo -e "${YELLOW}⚠️  警告: 不是樹梅派系統${NC}"
    read -p "繼續嗎? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 檢查用戶
if [[ $EUID -eq 0 ]]; then
    echo -e "${RED}❌ 請不要用 sudo 運行此腳本${NC}"
    exit 1
fi

# ═══════════════════════════════════════════════════════════════
# 步驟 1: 系統更新
# ═══════════════════════════════════════════════════════════════
echo -e "${CYAN}[1/7] 更新系統...${NC}"
sudo apt update
sudo apt upgrade -y
echo -e "${GREEN}✅ 系統已更新${NC}\n"

# ═══════════════════════════════════════════════════════════════
# 步驟 2: 安裝 Python 依賴
# ═══════════════════════════════════════════════════════════════
echo -e "${CYAN}[2/7] 安裝 Python 和依賴...${NC}"

sudo apt install -y \
    python3-pip \
    python3-dev \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    git \
    curl \
    wget \
    build-essential \
    libssl-dev \
    libffi-dev

# 設置 Python 3.11 為預設
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 2>/dev/null || true

python3 --version
pip3 --version

echo -e "${GREEN}✅ Python 已安裝${NC}\n"

# ═══════════════════════════════════════════════════════════════
# 步驟 3: 建立安裝目錄
# ═══════════════════════════════════════════════════════════════
echo -e "${CYAN}[3/7] 建立目錄...${NC}"

if [ -d "$INSTALL_PATH" ]; then
    echo -e "${YELLOW}⚠️  $INSTALL_PATH 已存在${NC}"
    read -p "覆蓋嗎? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo rm -rf "$INSTALL_PATH"
    fi
fi

sudo mkdir -p "$INSTALL_PATH"
sudo chown -R $USER:$USER "$INSTALL_PATH"

echo -e "${GREEN}✅ 目錄已建立: $INSTALL_PATH${NC}\n"

# ═══════════════════════════════════════════════════════════════
# 步驟 4: 複製或克隆程式碼
# ═══════════════════════════════════════════════════════════════
echo -e "${CYAN}[4/7] 複製代碼...${NC}"

# 檢查是否有本地備份 (USB 或網絡共享)
if [ -d "/mnt/usb/3dprint" ]; then
    echo "從 USB 複製..."
    cp -r /mnt/usb/3dprint/* "$INSTALL_PATH/"
elif [ -d "/mnt/share/3dprint" ]; then
    echo "從網絡共享複製..."
    cp -r /mnt/share/3dprint/* "$INSTALL_PATH/"
else
    echo "從 GitHub 克隆..."
    read -p "輸入 GitHub 倉庫 URL (或按 Enter 跳過): " GITHUB_URL
    if [ ! -z "$GITHUB_URL" ]; then
        git clone "$GITHUB_URL" "$INSTALL_PATH" || true
    else
        echo -e "${YELLOW}⚠️  跳過代碼複製，請手動複製檔案${NC}"
    fi
fi

if [ ! -f "$INSTALL_PATH/requirements.txt" ]; then
    echo -e "${RED}❌ 找不到 requirements.txt${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 代碼已複製${NC}\n"

# ═══════════════════════════════════════════════════════════════
# 步驟 5: 安裝 Python 依賴
# ═══════════════════════════════════════════════════════════════
echo -e "${CYAN}[5/7] 安裝 Python 依賴 (可能需要 5-10 分鐘)...${NC}"

cd "$INSTALL_PATH"
pip3 install --upgrade pip setuptools wheel
pip3 install -r requirements.txt --timeout=1000

echo -e "${GREEN}✅ Python 依賴已安裝${NC}\n"

# ═══════════════════════════════════════════════════════════════
# 步驟 6: 建立 Systemd 服務
# ═══════════════════════════════════════════════════════════════
echo -e "${CYAN}[6/7] 設置開機自啟動...${NC}"

# 監控系統服務
sudo tee /etc/systemd/system/printer-monitor.service > /dev/null <<EOF
[Unit]
Description=3D Printer Monitoring System
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_PATH
ExecStart=/usr/bin/python3 -m src.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# API 伺服器服務
sudo tee /etc/systemd/system/printer-api.service > /dev/null <<EOF
[Unit]
Description=3D Printer API Server
After=printer-monitor.service
Wants=printer-monitor.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_PATH
ExecStart=/usr/bin/python3 -m uvicorn src.api_server:app --host 0.0.0.0 --port $PORT
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 啟用服務
sudo systemctl daemon-reload
sudo systemctl enable printer-monitor.service
sudo systemctl enable printer-api.service

echo -e "${GREEN}✅ Systemd 服務已配置${NC}\n"

# ═══════════════════════════════════════════════════════════════
# 步驟 7: 可選優化
# ═══════════════════════════════════════════════════════════════
echo -e "${CYAN}[7/7] 系統優化...${NC}"

# 禁用藍牙 (節省資源)
sudo systemctl disable bluetooth.service 2>/dev/null || true

# 設置日誌輪轉
sudo tee /etc/logrotate.d/printer-monitor > /dev/null <<EOF
$INSTALL_PATH/printer_monitor.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 $USER $USER
}
EOF

echo -e "${GREEN}✅ 系統優化完成${NC}\n"

# ═══════════════════════════════════════════════════════════════
# 最終步驟
# ═══════════════════════════════════════════════════════════════

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        部署完成！ ✅                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}重要信息:${NC}"
echo "  📁 安裝路徑: $INSTALL_PATH"
echo "  🔧 配置檔: $INSTALL_PATH/config/printers.yaml"
echo "  📝 日誌: journalctl -u printer-monitor -f"
echo "  🌐 API 端口: $PORT"
echo ""

echo -e "${CYAN}下一步:${NC}"
echo "  1. 編輯配置檔並更新印表機 IP:"
echo "     nano $INSTALL_PATH/config/printers.yaml"
echo ""
echo "  2. 啟動服務:"
echo "     sudo systemctl start printer-monitor.service"
echo "     sudo systemctl start printer-api.service"
echo ""
echo "  3. 查看狀態:"
echo "     sudo systemctl status printer-monitor.service"
echo "     sudo systemctl status printer-api.service"
echo ""
echo "  4. 查看日誌:"
echo "     journalctl -u printer-monitor -f"
echo ""
echo "  5. 測試 API:"
echo "     curl http://localhost:$PORT/api/status"
echo ""

read -p "現在編輯配置檔嗎? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    nano "$INSTALL_PATH/config/printers.yaml"
fi

echo -e "${GREEN}部署完成！${NC}"
