# ============================================================
# 傳送 3D Printer Monitor 到樹莓派
# 用法: .\deploy\transfer_to_rpi.ps1 -RpiIP 192.168.0.xxx -RpiUser pi
# ============================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$RpiIP,

    [string]$RpiUser = "pi",
    [string]$RemoteDir = "~/3dprint"
)

$LocalDir = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host "=============================================="
Write-Host " 傳送 3D Printer Monitor 到樹莓派"
Write-Host "=============================================="
Write-Host " 來源: $LocalDir"
Write-Host " 目標: $RpiUser@$RpiIP`:$RemoteDir"
Write-Host ""

# 確認 SSH 可用
try {
    ssh -o ConnectTimeout=5 -o BatchMode=yes "$RpiUser@$RpiIP" "echo ok" 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "SSH 連線失敗" }
    Write-Host " SSH 連線: OK"
} catch {
    Write-Host " [!] SSH 連線失敗，請確認:"
    Write-Host "   1. 樹莓派已開機並連到同一個網路"
    Write-Host "   2. IP 位址正確: $RpiIP"
    Write-Host "   3. SSH 已啟用 (sudo raspi-config → Interfaces → SSH)"
    Write-Host "   4. 已設定 SSH key 或輸入密碼"
    exit 1
}

# 建立遠端目錄
Write-Host " 建立遠端目錄..."
ssh "$RpiUser@$RpiIP" "mkdir -p $RemoteDir/src $RemoteDir/config $RemoteDir/data $RemoteDir/tools $RemoteDir/deploy"

# 傳送核心檔案
Write-Host " 傳送檔案..."

$files = @(
    "run.py",
    "requirements.txt",
    "src/__init__.py",
    "src/main.py",
    "src/printer_base.py",
    "src/bambu_monitor.py",
    "src/creality_monitor.py",
    "src/api_server.py",
    "src/data_store.py",
    "src/print_history.py",
    "src/printer_profiles.py",
    "src/printer_control.py",
    "src/camera_sync.py",
    "tools/check_status.py",
    "deploy/setup.sh"
)

foreach ($f in $files) {
    $local  = Join-Path $LocalDir $f
    $remote = "$RpiUser@$RpiIP`:$RemoteDir/$f"
    if (Test-Path $local) {
        scp -q $local $remote
        Write-Host "  ✓ $f"
    } else {
        Write-Host "  - $f (找不到，跳過)"
    }
}

# 傳送設定檔 (如果存在)
$configFile = Join-Path $LocalDir "config\printers.yaml"
if (Test-Path $configFile) {
    scp -q $configFile "$RpiUser@$RpiIP`:$RemoteDir/config/printers.yaml"
    Write-Host "  ✓ config/printers.yaml"
}

# 轉換換行符（Windows CRLF → Unix LF）
Write-Host ""
Write-Host " 轉換換行符..."
ssh "$RpiUser@$RpiIP" "find $RemoteDir -name '*.py' -o -name '*.sh' -o -name '*.yaml' | xargs sed -i 's/\r//' 2>/dev/null; chmod +x $RemoteDir/deploy/setup.sh"

Write-Host ""
Write-Host "=============================================="
Write-Host " 傳送完成！"
Write-Host "=============================================="
Write-Host ""
Write-Host " 下一步，在樹莓派上執行："
Write-Host "   ssh $RpiUser@$RpiIP"
Write-Host "   cd $RemoteDir"
Write-Host "   bash deploy/setup.sh"
Write-Host ""
