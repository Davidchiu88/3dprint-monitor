@echo off
chcp 65001 > nul
cls

echo =====================================================
echo  3D 列印監控系統 - 伺服器啟動
echo =====================================================
echo.

REM 檢查 Python
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ 錯誤: 找不到 Python
    echo    請確保 Python 已安裝且在 PATH 中
    pause
    exit /b 1
)

REM 設置工作目錄
cd /d "%~dp0"
if errorlevel 1 (
    echo ❌ 錯誤: 無法切換目錄
    pause
    exit /b 1
)

REM 檢查配置檔
if not exist "config\printers.yaml" (
    echo ❌ 錯誤: 未找到配置檔 config\printers.yaml
    pause
    exit /b 1
)

echo ✅ 環境檢查通過
echo.

REM 顯示配置信息
echo 配置檔:
python -c "import yaml; cfg=yaml.safe_load(open('config/printers.yaml')); print(f'  印表機數量: {len(cfg.get(\"printers\", []))}'); [print(f'    - {p[\"name\"]} ({p[\"type\"]})') for p in cfg.get('printers', [])]" 2>nul

echo.
echo 【1】啟動完整系統（監控 + API 伺服器）
echo 【2】僅啟動 API 伺服器
echo 【3】僅啟動監控系統
echo.
set /p choice="請選擇 [1-3]: "

if "%choice%"=="1" (
    echo.
    echo 啟動完整系統...
    echo.
    call :start_both
) else if "%choice%"=="2" (
    echo.
    echo 啟動 API 伺服器...
    echo.
    call :start_api
) else if "%choice%"=="3" (
    echo.
    echo 啟動監控系統...
    echo.
    call :start_monitor
) else (
    echo 無效選擇
    exit /b 1
)

pause
exit /b 0

REM ===== 子程式 =====

:start_both
echo 【步驟1】啟動監控系統 (背景)
start "3D 列印監控系統" python -m src.main
timeout /t 3 /nobreak
echo ✅ 監控系統已啟動
echo.

echo 【步驟2】啟動 API 伺服器 (port 7000)
echo 訪問地址: http://localhost:7000
echo 文檔: http://localhost:7000/docs
echo.
uvicorn src.api_server:app --host 0.0.0.0 --port 7000
exit /b 0

:start_api
echo 啟動 API 伺服器 (port 7000)
echo 訪問地址: http://localhost:7000
echo 文檔: http://localhost:7000/docs
echo.
echo 注意: 此模式下監控系統不運行，僅可查詢已保存的狀態
echo.
uvicorn src.api_server:app --host 0.0.0.0 --port 7000
exit /b 0

:start_monitor
echo 啟動監控系統
echo 日誌: printer_monitor.log
echo.
echo 注意: 此模式下 API 伺服器不運行
echo.
python -m src.main
exit /b 0
