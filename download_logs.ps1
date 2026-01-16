# PowerShell скрипт для скачивания логов с сервера
# Использование: .\download_logs.ps1 [API_URL] [API_TOKEN]

param(
    [string]$ApiUrl = $env:REALTY_API_URL,
    [string]$ApiToken = $env:REALTY_API_TOKEN
)

# Конфигурация
if (-not $ApiUrl) {
    $ApiUrl = "http://localhost"  # Или ваш домен
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LocalLogsDir = Join-Path $ScriptDir "logs_server"

# Типы логов
$LogTypes = @('app', 'errors', 'bot', 'bot_errors')
$LogFilenames = @{
    'app' = 'app.log'
    'errors' = 'errors.log'
    'bot' = 'bot.log'
    'bot_errors' = 'bot_errors.log'
}

# Получить токен если не указан
if (-not $ApiToken) {
    $TokenFile = Join-Path $ScriptDir ".api_token"
    if (Test-Path $TokenFile) {
        $ApiToken = Get-Content $TokenFile -Raw | ForEach-Object { $_.Trim() }
    } else {
        Write-Host "⚠️  API токен не найден!" -ForegroundColor Yellow
        Write-Host "   Передайте токен как параметр: .\download_logs.ps1 -ApiUrl <URL> -ApiToken <TOKEN>"
        Write-Host "   Или создайте файл .api_token с токеном"
        Write-Host ""
        $ApiToken = Read-Host "Введите API токен (или Enter чтобы выйти)"
        if (-not $ApiToken) {
            exit 1
        }
    }
}

# Получить URL если передан как аргумент
if ($args.Count -gt 0 -and -not $ApiUrl) {
    $ApiUrl = $args[0]
}
if ($args.Count -gt 1 -and -not $ApiToken) {
    $ApiToken = $args[1]
}

Write-Host "🔄 Скачивание логов с сервера..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Сервер: $ApiUrl"
Write-Host "Папка: $LocalLogsDir"
Write-Host ""

# Создать папку если не существует
if (-not (Test-Path $LocalLogsDir)) {
    New-Item -ItemType Directory -Path $LocalLogsDir | Out-Null
}

$successCount = 0

foreach ($logType in $LogTypes) {
    $filename = $LogFilenames[$logType]
    $url = "$ApiUrl/api/logs/file/$logType"
    $outputPath = Join-Path $LocalLogsDir $filename
    
    Write-Host "Скачивание $logType... " -NoNewline
    
    try {
        $headers = @{
            'Authorization' = "Bearer $ApiToken"
        }
        
        $response = Invoke-WebRequest -Uri $url -Headers $headers -OutFile $outputPath -TimeoutSec 30
        
        $fileSize = (Get-Item $outputPath).Length / 1KB
        Write-Host "✅ $filename ($([math]::Round($fileSize, 1)) KB)" -ForegroundColor Green
        $successCount++
    } catch {
        if ($_.Exception.Response.StatusCode -eq 404) {
            Write-Host "⚠️  $filename - файл не найден на сервере" -ForegroundColor Yellow
        } else {
            Write-Host "❌ $filename - ошибка: $_" -ForegroundColor Red
        }
    }
}

Write-Host ""
if ($successCount -gt 0) {
    Write-Host "✅ Скачано файлов: $successCount/$($LogTypes.Count)" -ForegroundColor Green
    Write-Host "📁 Логи находятся в: $LocalLogsDir" -ForegroundColor Cyan
} else {
    Write-Host "❌ Не удалось скачать ни одного файла" -ForegroundColor Red
    Write-Host "   Проверьте API URL и токен" -ForegroundColor Yellow
    exit 1
}

