#!/bin/bash
# 從 Windows PC 更新程式碼後，在樹莓派上執行此腳本熱更新
# 用法: bash deploy/update_rpi.sh

PROJECT_DIR="$HOME/3dprint"
cd "$PROJECT_DIR"

echo ">>> 重新啟動 3D Printer Monitor..."
sudo systemctl restart 3dprint-monitor.service
sleep 2

echo ">>> 服務狀態："
sudo systemctl status 3dprint-monitor.service --no-pager -l | head -20

echo ""
echo ">>> API 健康檢查："
sleep 3
curl -s http://localhost:7000/api/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  狀態: {d[\"status\"]}, 時間: {d[\"timestamp\"]}')" 2>/dev/null || echo "  API 未就緒，請稍後再試"
