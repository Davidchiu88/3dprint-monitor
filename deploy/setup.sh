#!/bin/bash
# ============================================================
# 3D Printer Monitor - Raspberry Pi 自動安裝腳本
# 用法: bash setup.sh
# ============================================================

set -e

PROJECT_DIR="$HOME/3dprint"
SERVICE_USER="$USER"
PYTHON="python3"

echo ""
echo "=============================================="
echo " 3D Printer Monitor - Raspberry Pi 安裝"
echo "=============================================="
echo " 安裝目錄: $PROJECT_DIR"
echo " 執行使用者: $SERVICE_USER"
echo ""

# ── 1. 確認 Python 版本 ─────────────────────────────────────
echo ">>> [1/6] 檢查 Python 版本..."
PY_VER=$($PYTHON --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
PY_MAJOR=$(echo $PY_VER | cut -d. -f1)
PY_MINOR=$(echo $PY_VER | cut -d. -f2)
echo "  Python $PY_VER"
if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]); then
    echo "  [!] 需要 Python 3.9+，正在安裝..."
    sudo apt-get update -qq
    sudo apt-get install -y python3 python3-pip python3-venv
fi

# ── 2. 安裝系統依賴 ─────────────────────────────────────────
echo ""
echo ">>> [2/6] 安裝系統依賴..."
sudo apt-get update -qq
sudo apt-get install -y python3-pip python3-venv git curl wget libssl-dev

# ── 3. 建立 virtualenv ─────────────────────────────────────
echo ""
echo ">>> [3/6] 建立 Python 虛擬環境..."
cd "$PROJECT_DIR"
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    echo "  虛擬環境建立完成"
else
    echo "  虛擬環境已存在，跳過"
fi

# 啟動 venv 並安裝套件
source venv/bin/activate
echo ""
echo ">>> [4/6] 安裝 Python 套件..."
pip install --upgrade pip -q
pip install \
    paho-mqtt>=2.0 \
    requests \
    pyyaml \
    websockets>=11.0 \
    fastapi==0.111.0 \
    uvicorn==0.29.0 \
    python-dotenv \
    -q
echo "  套件安裝完成"
deactivate

# ── 4. 建立 data 目錄 ────────────────────────────────────────
echo ""
echo ">>> [5/6] 建立資料目錄..."
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/config"
chmod 755 "$PROJECT_DIR/data"

# ── 5. 安裝 systemd 服務 ─────────────────────────────────────
echo ""
echo ">>> [6/6] 安裝 systemd 服務..."

# Monitor service
MONITOR_SERVICE="/etc/systemd/system/3dprint-monitor.service"
sudo tee "$MONITOR_SERVICE" > /dev/null << EOF
[Unit]
Description=3D Printer Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python run.py
Restart=always
RestartSec=15
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONIOENCODING=utf-8

[Install]
WantedBy=multi-user.target
EOF
echo "  已建立: $MONITOR_SERVICE"

# ── 6. 安裝 Cloudflare Tunnel ────────────────────────────────
echo ""
read -p "是否安裝 Cloudflare Tunnel 服務？(y/N) " install_tunnel
if [[ "$install_tunnel" =~ ^[Yy]$ ]]; then
    # Download cloudflared
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ]; then
        CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
    elif [ "$ARCH" = "armv7l" ]; then
        CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm"
    else
        CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    fi

    echo "  下載 cloudflared ($ARCH)..."
    wget -q "$CF_URL" -O "$PROJECT_DIR/cloudflared"
    chmod +x "$PROJECT_DIR/cloudflared"

    TUNNEL_SERVICE="/etc/systemd/system/3dprint-tunnel.service"
    sudo tee "$TUNNEL_SERVICE" > /dev/null << EOF
[Unit]
Description=3D Printer Monitor - Cloudflare Tunnel
After=network-online.target 3dprint-monitor.service
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
ExecStart=$PROJECT_DIR/cloudflared tunnel --url http://localhost:7000 --no-autoupdate
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    echo "  已建立: $TUNNEL_SERVICE"
fi

# ── 7. 啟用並啟動服務 ────────────────────────────────────────
echo ""
sudo systemctl daemon-reload
sudo systemctl enable 3dprint-monitor.service
sudo systemctl start  3dprint-monitor.service

if [ -f "/etc/systemd/system/3dprint-tunnel.service" ]; then
    sudo systemctl enable 3dprint-tunnel.service
    sudo systemctl start  3dprint-tunnel.service
fi

# ── 8. 完成 ──────────────────────────────────────────────────
echo ""
echo "=============================================="
echo " 安裝完成！"
echo "=============================================="
echo ""
echo " 常用指令："
echo "   查看狀態:  sudo systemctl status 3dprint-monitor"
echo "   查看 log:  sudo journalctl -u 3dprint-monitor -f"
echo "   重啟服務:  sudo systemctl restart 3dprint-monitor"
echo "   停止服務:  sudo systemctl stop 3dprint-monitor"
if [ -f "/etc/systemd/system/3dprint-tunnel.service" ]; then
    echo "   Tunnel log:sudo journalctl -u 3dprint-tunnel -f"
fi
echo ""
echo " API 伺服器: http://$(hostname -I | awk '{print $1}'):7000"
echo " 健康檢查:   curl http://localhost:7000/api/health"
echo ""

# 顯示 Tunnel URL (如果有安裝)
if [ -f "/etc/systemd/system/3dprint-tunnel.service" ]; then
    echo " Cloudflare Tunnel URL (等 15 秒讀取...):"
    sleep 15
    sudo journalctl -u 3dprint-tunnel --no-pager -n 20 | grep -o 'https://[^ ]*trycloudflare[^ ]*' | tail -1
fi
