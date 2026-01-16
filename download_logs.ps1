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

# Типы ТЕСТОВЫХ логов (короткие, свежие логи для AI)
$TestLogTypes = @('test_app', 'test_errors', 'test_database', 'test_api', 'test_celery', 'test_bot', 'test_bot_errors')
$TestLogFilenames = @{
    'test_app' = 'test_app.log'
    'test_errors' = 'test_errors.log'
    'test_database' = 'test_database.log'
    'test_api' = 'test_api.log'
    'test_celery' = 'test_celery.log'
    'test_bot' = 'test_bot.log'
    'test_bot_errors' = 'test_bot_errors.log'
}

# Получить токен если не указан
if (-not $ApiToken) {
    $ApiToken = $env:REALTY_LOGS_DOWNLOAD_TOKEN
}
if (-not $ApiToken) {
    $TokenFile = Join-Path $ScriptDir ".api_token"
    if (Test-Path $TokenFile) {
        $ApiToken = Get-Content $TokenFile -Raw | ForEach-Object { $_.Trim() }
    } else {
        Write-Host "⚠️  LOGS_DOWNLOAD_TOKEN не найден!" -ForegroundColor Yellow
        Write-Host "   Это отдельный токен для скачивания логов (не JWT)."
        Write-Host "   Передайте токен как параметр: .\download_logs.ps1 -ApiUrl <URL> -ApiToken <TOKEN>"
        Write-Host "   Или создайте файл .api_token с токеном"
        Write-Host "   Или установите переменную: `$env:REALTY_LOGS_DOWNLOAD_TOKEN = 'token'"
        Write-Host ""
        Write-Host "   Токен настраивается на сервере в переменной окружения LOGS_DOWNLOAD_TOKEN"
        Write-Host ""
        $ApiToken = Read-Host "Введите LOGS_DOWNLOAD_TOKEN (или Enter чтобы выйти)"
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

Write-Host "🔄 Скачивание тестовых логов с сервера..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Сервер: $ApiUrl"
Write-Host "Папка: $LocalLogsDir"
Write-Host ""
Write-Host "📥 Скачивание тестовых логов (свежие логи с последнего деплоя)..." -ForegroundColor Cyan
Write-Host ""

# Создать папку если не существует
if (-not (Test-Path $LocalLogsDir)) {
    New-Item -ItemType Directory -Path $LocalLogsDir | Out-Null
}

$successCount = 0

foreach ($logType in $TestLogTypes) {
    $filename = $TestLogFilenames[$logType]
    $url = "$ApiUrl/api/logs/file/$logType"
    $outputPath = Join-Path $LocalLogsDir $filename
    
    Write-Host "Скачивание $logType... " -NoNewline
    
    try {
        # Use token as query parameter (LOGS_DOWNLOAD_TOKEN)
        $urlWithToken = "$url" + "?token=" + [System.Web.HttpUtility]::UrlEncode($ApiToken)
        
        $response = Invoke-WebRequest -Uri $urlWithToken -Method Get -OutFile $outputPath -TimeoutSec 30
        
        $fileSize = (Get-Item $outputPath).Length / 1KB
        Write-Host "✅ $filename ($([math]::Round($fileSize, 1)) KB)" -ForegroundColor Green
        $successCount++
    } catch {
        if ($_.Exception.Response.StatusCode -eq 404) {
            Write-Host "⚠️  $filename - файл не найден на сервере" -ForegroundColor Yellow
        } elseif ($_.Exception.Response.StatusCode -eq 401) {
            Write-Host "❌ $filename - неверный токен" -ForegroundColor Red
        } else {
            Write-Host "❌ $filename - ошибка: $_" -ForegroundColor Red
        }
    }
}

Write-Host ""
if ($successCount -gt 0) {
    Write-Host "✅ Скачано файлов: $successCount/$($TestLogTypes.Count)" -ForegroundColor Green
    Write-Host "📁 Тестовые логи находятся в: $LocalLogsDir" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "💡 Эти логи содержат только события с последнего деплоя" -ForegroundColor Yellow
    Write-Host "   (очищаются при каждом deploy.sh для свежего анализа)" -ForegroundColor Yellow
} else {
    Write-Host "❌ Не удалось скачать ни одного файла" -ForegroundColor Red
    Write-Host "   Проверьте:" -ForegroundColor Yellow
    Write-Host "   1. API URL правильный"
    Write-Host "   2. LOGS_DOWNLOAD_TOKEN действителен (настроен на сервере)"
    Write-Host "   3. Сервер доступен"
    Write-Host "   4. deploy.sh был запущен (логи могли быть очищены)"
    exit 1
}

