@echo off
:: 3D Printer Monitor - Cloudflare Tunnel 啟動器
:: 自動下載 cloudflared 並建立 HTTPS tunnel
::
:: 啟動後會顯示如: https://abc-xyz-123.trycloudflare.com
:: 把這個 URL 複製到 printers.html 設定頁面

setlocal
set PORT=7000
set CLOUDFLARED=%~dp0cloudflared.exe

echo ==========================================
echo  3D Printer Monitor - Cloudflare Tunnel
echo ==========================================
echo.

:: Download cloudflared if not present
if not exist "%CLOUDFLARED%" (
    echo Downloading cloudflared...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%CLOUDFLARED%'"
    echo Done.
    echo.
)

:: Check if monitor is running
curl -s http://localhost:%PORT%/api/health >nul 2>&1
if errorlevel 1 (
    echo [!] API server not running on port %PORT%
    echo     Please start: python run.py
    echo.
)

echo Starting tunnel for http://localhost:%PORT%...
echo.
echo Copy the URL shown below and paste it into printers.html settings.
echo (Format: https://xxxx.trycloudflare.com)
echo.
echo Press Ctrl+C to stop the tunnel.
echo.

"%CLOUDFLARED%" tunnel --url http://localhost:%PORT%
