#!/usr/bin/env pwsh
# 3D 列印監控系統伺服器啟動腳本

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host @"
=====================================================
 3D 列印監控系統 - 伺服器啟動
=====================================================
"@ -ForegroundColor Cyan

# 檢查 Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 錯誤: 找不到 Python" -ForegroundColor Red
    Write-Host "   請確保 Python 已安裝且在 PATH 中"
    exit 1
}

# 切換目錄
Set-Location $PSScriptRoot
Write-Host "📁 工作目錄: $(Get-Location)" -ForegroundColor Cyan

# 檢查配置
if (-not (Test-Path "config\printers.yaml")) {
    Write-Host "❌ 錯誤: 未找到配置檔 config\printers.yaml" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 配置檔存在" -ForegroundColor Green

# 讀取配置信息
try {
    $config = python -c "import yaml; cfg=yaml.safe_load(open('config/printers.yaml')); [print(f'{p[\"name\"]} ({p[\"type\"]})') for p in cfg.get('printers', [])]" 2>$null
    Write-Host "`n📋 配置的印表機:" -ForegroundColor Cyan
    $config | ForEach-Object { Write-Host "  • $_" }
} catch {
    Write-Host "⚠️  無法讀取配置詳情" -ForegroundColor Yellow
}

Write-Host "`n選擇啟動模式:" -ForegroundColor Cyan
Write-Host "  【1】完整系統（監控 + API）- 推薦"
Write-Host "  【2】API 伺服器只"
Write-Host "  【3】監控系統只"
Write-Host ""

$choice = Read-Host "請輸入 [1-3]"

switch ($choice) {
    "1" {
        Start-FullSystem
    }
    "2" {
        Start-APIServer
    }
    "3" {
        Start-Monitor
    }
    default {
        Write-Host "❌ 無效選擇" -ForegroundColor Red
        exit 1
    }
}

# ===== 函式 =====

function Start-FullSystem {
    Write-Host "`n【步驟1】啟動監控系統 (背景)..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python -m src.main" `
        -WindowStyle Normal
    Start-Sleep -Seconds 3
    Write-Host "✅ 監控系統已啟動`n" -ForegroundColor Green

    Write-Host "【步驟2】啟動 API 伺服器..." -ForegroundColor Green
    Write-Host "  監聽: http://0.0.0.0:7000" -ForegroundColor Cyan
    Write-Host "  API 文檔: http://localhost:7000/docs" -ForegroundColor Cyan
    Write-Host "  WebUI 預覽: http://localhost:3000 (如已安裝前端)`n" -ForegroundColor Cyan

    uvicorn src.api_server:app --host 0.0.0.0 --port 7000
}

function Start-APIServer {
    Write-Host "啟動 API 伺服器..." -ForegroundColor Green
    Write-Host "  監聽: http://0.0.0.0:7000" -ForegroundColor Cyan
    Write-Host "  API 文檔: http://localhost:7000/docs" -ForegroundColor Cyan
    Write-Host "`n⚠️  注意: 監控系統未運行，僅可查詢已保存的狀態`n" -ForegroundColor Yellow

    uvicorn src.api_server:app --host 0.0.0.0 --port 7000
}

function Start-Monitor {
    Write-Host "啟動監控系統..." -ForegroundColor Green
    Write-Host "  日誌: printer_monitor.log" -ForegroundColor Cyan
    Write-Host "`n⚠️  注意: API 伺服器未運行`n" -ForegroundColor Yellow

    python -m src.main
}
