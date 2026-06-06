#!/bin/bash
# 3D Printer Monitor - Cloudflare Tunnel (Linux/Raspberry Pi)
PORT=7000

echo "======================================"
echo " 3D Printer Monitor - Cloudflare Tunnel"
echo "======================================"

# Install cloudflared if not present
if ! command -v cloudflared &> /dev/null; then
    echo "Installing cloudflared..."
    arch=$(uname -m)
    if [ "$arch" = "aarch64" ] || [ "$arch" = "armv7l" ]; then
        # Raspberry Pi
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -O /usr/local/bin/cloudflared
    else
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared
    fi
    chmod +x /usr/local/bin/cloudflared
    echo "Done."
fi

# Check monitor running
if ! curl -s http://localhost:$PORT/api/health > /dev/null; then
    echo "[!] API server not running on port $PORT"
    echo "    Please start: python3 run.py &"
fi

echo ""
echo "Starting tunnel for http://localhost:$PORT..."
echo "Copy the https://xxxx.trycloudflare.com URL to printers.html settings"
echo ""
cloudflared tunnel --url http://localhost:$PORT
