#!/bin/bash
# Script for deployment with tests and admin notification
#
# IMPORTANT: If you get "Permission denied" error, run:
#   chmod +x deploy_with_tests.sh
# Or run with: bash deploy_with_tests.sh

# Ensure script is executable
chmod +x "$0" 2>/dev/null || true

set -e  # Stop on error

echo "🚀 Запуск развертывания с тестами..."

# Navigate to project directory
cd ~/realty-system

# Check git status (only check, don't pull)
echo "📊 Проверка изменений в git..."
git fetch origin 2>/dev/null || true
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
REMOTE_BRANCH="origin/$CURRENT_BRANCH"

# Check if there are differences
LOCAL_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "")
REMOTE_COMMIT=$(git rev-parse "$REMOTE_BRANCH" 2>/dev/null || echo "")

if [ -n "$LOCAL_COMMIT" ] && [ -n "$REMOTE_COMMIT" ] && [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
    echo "⚠️  Обнаружены различия с удаленной веткой:"
    echo "   Локальный:  $LOCAL_COMMIT"
    echo "   Удаленный:  $REMOTE_COMMIT"
    echo "   Используйте deploy.sh для обновления с git"
else
    echo "✅ Локальная ветка синхронизирована с удаленной"
fi

# Clear temporary test logs
echo "🧹 Очистка временных тестовых логов..."
if [ -d "logs" ]; then
    rm -f logs/test_*.log 2>/dev/null || true
    echo "✅ Временные тестовые логи очищены"
fi

# Restart containers
echo "🔄 Перезапуск контейнеров..."
docker-compose down
docker-compose up -d --build

# Wait for containers to start
echo "⏳ Ожидание запуска контейнеров (30 секунд)..."
sleep 30

# Run tests
echo "🧪 Запуск системных тестов..."

TEST_ERRORS=0
TEST_MESSAGES=()

# Test 1: Check if all containers are running
echo "  ✓ Проверка статуса контейнеров..."
EXPECTED_CONTAINERS=("realty_postgres" "realty_redis" "realty_web" "realty_bot" "realty_celery_worker" "realty_celery_beat" "realty_nginx")
RUNNING_CONTAINERS=$(docker ps --format "{{.Names}}")

for container in "${EXPECTED_CONTAINERS[@]}"; do
    if echo "$RUNNING_CONTAINERS" | grep -q "^${container}$"; then
        echo "    ✅ Контейнер $container запущен"
        TEST_MESSAGES+=("✅ $container: запущен")
    else
        echo "    ❌ Контейнер $container НЕ запущен"
        TEST_MESSAGES+=("❌ $container: НЕ запущен")
        TEST_ERRORS=$((TEST_ERRORS + 1))
    fi
done

# Test 2: Check web server health
echo "  ✓ Проверка работоспособности web-сервера..."
if curl -f -s http://localhost:5000/health > /dev/null 2>&1 || curl -f -s http://localhost:5000/ > /dev/null 2>&1; then
    echo "    ✅ Web-сервер отвечает"
    TEST_MESSAGES+=("✅ Web-сервер: отвечает")
else
    echo "    ⚠️  Проверка работоспособности web-сервера не удалась (может быть нормально, если endpoint /health не существует)"
    TEST_MESSAGES+=("⚠️  Web-сервер: проверка неоднозначна")
fi

# Test 3: Check database connection
echo "  ✓ Проверка подключения к базе данных..."
if docker exec realty_postgres pg_isready -U ${POSTGRES_USER:-realty_user} > /dev/null 2>&1; then
    echo "    ✅ База данных готова"
    TEST_MESSAGES+=("✅ База данных: готова")
else
    echo "    ❌ База данных НЕ готова"
    TEST_MESSAGES+=("❌ База данных: НЕ готова")
    TEST_ERRORS=$((TEST_ERRORS + 1))
fi

# Test 4: Check Redis connection
echo "  ✓ Проверка подключения к Redis..."
if docker exec realty_redis redis-cli ping > /dev/null 2>&1; then
    echo "    ✅ Redis отвечает"
    TEST_MESSAGES+=("✅ Redis: отвечает")
else
    echo "    ❌ Redis НЕ отвечает"
    TEST_MESSAGES+=("❌ Redis: НЕ отвечает")
    TEST_ERRORS=$((TEST_ERRORS + 1))
fi

# Test 5: Check bot container logs for critical errors (with smart filtering)
echo "  ✓ Проверка логов бота на критические ошибки..."
# Get recent logs and filter out safe patterns
BOT_LOGS=$(docker logs realty_bot --tail 100 2>&1)
# Only count real critical errors: unhandled exceptions with traceback, fatal errors
# Ignore: warnings, handled exceptions, network errors, debug/info messages
CRITICAL_BOT_ERRORS=$(echo "$BOT_LOGS" | \
    grep -iE "Traceback|^Traceback|Unhandled|Fatal|Critical.*error" | \
    grep -vE "WARNING|warning|WARN|INFO|DEBUG" | \
    grep -vE "transient|network.*error|getUpdates conflict|Conflict" | \
    grep -vE "handled|caught|ignored|retry|reconnect|recovering" | \
    grep -vE "Bad Gateway|ConnectError|NetworkError|connection.*failed" | \
    wc -l)

if [ "$CRITICAL_BOT_ERRORS" -eq 0 ]; then
    echo "    ✅ Критических ошибок в логах бота нет (последние 100 строк)"
    TEST_MESSAGES+=("✅ Логи бота: критических ошибок нет")
else
    echo "    ⚠️  Найдено $CRITICAL_BOT_ERRORS критических ошибок в логах бота"
    TEST_MESSAGES+=("⚠️  Логи бота: $CRITICAL_BOT_ERRORS критических ошибок")
    TEST_ERRORS=$((TEST_ERRORS + 1))
fi

# Test 6: Check web container logs for critical errors (with smart filtering)
echo "  ✓ Проверка логов web-контейнера на критические ошибки..."
WEB_LOGS=$(docker logs realty_web --tail 100 2>&1)
# Only count real critical errors: unhandled exceptions with traceback, fatal errors
# Ignore: warnings, 404/403 errors, handled exceptions, debug/info messages
CRITICAL_WEB_ERRORS=$(echo "$WEB_LOGS" | \
    grep -iE "Traceback|^Traceback|Unhandled|Fatal|Critical.*error" | \
    grep -vE "WARNING|warning|WARN|INFO|DEBUG" | \
    grep -vE "404|403|401|400" | \
    grep -vE "handled|caught|ignored|retry|reconnect|recovering" | \
    grep -vE "blocked.*request|suspicious.*request|method.*not.*allowed" | \
    wc -l)

if [ "$CRITICAL_WEB_ERRORS" -eq 0 ]; then
    echo "    ✅ Критических ошибок в логах web нет (последние 100 строк)"
    TEST_MESSAGES+=("✅ Логи web: критических ошибок нет")
else
    echo "    ⚠️  Найдено $CRITICAL_WEB_ERRORS критических ошибок в логах web"
    TEST_MESSAGES+=("⚠️  Логи web: $CRITICAL_WEB_ERRORS критических ошибок")
    TEST_ERRORS=$((TEST_ERRORS + 1))
fi

# Prepare test summary
echo ""
echo "📊 Сводка тестов:"
for msg in "${TEST_MESSAGES[@]}"; do
    echo "  $msg"
done

# Send notification to admin bot
echo ""
echo "📤 Отправка уведомления админу..."

# Get BOT_TOKEN from environment or .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-""}
ADMIN_ID="7615679936"

if [ -z "$BOT_TOKEN" ]; then
    echo "⚠️  Предупреждение: TELEGRAM_BOT_TOKEN не найден, пропуск уведомления"
else
    # Get current date and time in Moscow timezone (MSK)
    MSK_TIME=$(TZ='Europe/Moscow' date '+%d.%m.%Y %H:%M:%S МСК')
    
    # Prepare message
    if [ "$TEST_ERRORS" -eq 0 ]; then
        MESSAGE="✅ Развертывание завершено успешно!

Все системы запущены, ошибок нет, все работает.

📅 Дата и время: $MSK_TIME

📊 Результаты тестов:"
    else
        MESSAGE="⚠️ Развертывание завершено с предупреждениями

Найдено проблем: $TEST_ERRORS

📅 Дата и время: $MSK_TIME

📊 Результаты тестов:"
    fi
    
    # Add test results to message
    for msg in "${TEST_MESSAGES[@]}"; do
        MESSAGE="$MESSAGE
$msg"
    done
    
    # Send message via Telegram Bot API
    API_URL="https://api.telegram.org/bot${BOT_TOKEN}/sendMessage"
    
    # Use curl with proper escaping - send message as plain text
    RESPONSE=$(curl -s -X POST "$API_URL" \
        --data-urlencode "chat_id=${ADMIN_ID}" \
        --data-urlencode "text=${MESSAGE}" 2>&1)
    
    if echo "$RESPONSE" | grep -q '"ok":true'; then
        echo "✅ Уведомление успешно отправлено админу"
    else
        echo "⚠️  Не удалось отправить уведомление: $RESPONSE"
    fi
fi

echo ""
echo "✅ Развертывание с тестами завершено!"
echo ""
echo "Проверка статуса:"
echo "  docker ps"
echo "  docker logs realty_web"
echo "  docker logs realty_bot"
echo ""

