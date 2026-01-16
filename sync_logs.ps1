# PowerShell script to sync logs from server to local project
# Usage: .\sync_logs.ps1 [server_user] [server_host] [server_path]

param(
    [string]$ServerUser = "root",
    [string]$ServerHost = "msk-1-vm-vgtr",
    [string]$ServerPath = "~/realty-system/logs"
)

$LocalPath = "logs_server"

Write-Host "🔄 Syncing logs from server..." -ForegroundColor Green
Write-Host "Server: ${ServerUser}@${ServerHost}:${ServerPath}"
Write-Host "Local: ${LocalPath}/" 
Write-Host ""

# Create local directory if it doesn't exist
if (!(Test-Path $LocalPath)) {
    New-Item -ItemType Directory -Path $LocalPath | Out-Null
}

# Check if rsync is available (if using WSL)
$rsyncAvailable = Get-Command rsync -ErrorAction SilentlyContinue
if ($rsyncAvailable) {
    Write-Host "Using rsync..." -ForegroundColor Yellow
    wsl rsync -avz --progress `
        --exclude='*.log.*' `
        --include='*.log' `
        "${ServerUser}@${ServerHost}:${ServerPath}/" `
        "${LocalPath}/"
} elseif (Get-Command scp -ErrorAction SilentlyContinue) {
    Write-Host "Using scp..." -ForegroundColor Yellow
    # Use scp through WSL or native OpenSSH
    if (Get-Command wsl -ErrorAction SilentlyContinue) {
        wsl scp "${ServerUser}@${ServerHost}:${ServerPath}/*.log" "${LocalPath}/"
    } else {
        scp "${ServerUser}@${ServerHost}:${ServerPath}/*.log" "${LocalPath}/"
    }
} else {
    Write-Host "❌ Error: Neither rsync nor scp found. Please install OpenSSH or use WSL." -ForegroundColor Red
    exit 1
}

# Check if .gitignore exists and add entry
if (!(Get-Content .gitignore -ErrorAction SilentlyContinue | Select-String -Pattern "^logs_server/")) {
    Add-Content -Path .gitignore -Value "logs_server/"
    Write-Host "✅ Added logs_server/ to .gitignore" -ForegroundColor Green
}

Write-Host ""
Write-Host "✅ Logs synced successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Logs are available in: ${LocalPath}/"
Write-Host ""
Write-Host "Files:"
Get-ChildItem $LocalPath -ErrorAction SilentlyContinue | Format-Table Name, Length, LastWriteTime

