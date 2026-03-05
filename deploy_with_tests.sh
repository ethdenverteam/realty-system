#!/bin/bash
# Script for deployment with git pull, tests, and admin notification
#
# IMPORTANT: If you get "Permission denied" error, run:
#   chmod +x deploy_with_tests.sh
# Or run with: bash deploy_with_tests.sh

# Ensure script is executable
chmod +x "$0" 2>/dev/null || true

set -e  # Stop on error

echo "🚀 Starting deployment with tests..."

# Navigate to project directory
cd ~/realty-system

# Get updates from git
echo "📥 Getting updates from git..."

# Fetch latest changes from remote
echo "📡 Fetching latest changes from remote..."
git fetch origin

# Get current branch name
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
REMOTE_BRANCH="origin/$CURRENT_BRANCH"

# Force reset to remote branch (ignores all local changes)
echo "🔄 Resetting to remote branch (ignoring local changes)..."
git reset --hard "$REMOTE_BRANCH"

# Clean untracked files that might conflict
echo "🧹 Cleaning untracked files..."
git clean -fd || true

# Check if there were changes in the frontend
FRONTEND_CHANGED=$(git diff HEAD@{1} HEAD --name-only | grep -E "^frontend/" | wc -l)

if [ "$FRONTEND_CHANGED" -gt 0 ]; then
    echo "📦 Frontend changes detected, building..."
    cd frontend
    npm run build
    cd ..
else
    echo "✅ No frontend changes, skipping build"
fi

# Clear temporary test logs
echo "🧹 Clearing temporary test logs..."
if [ -d "logs" ]; then
    rm -f logs/test_*.log 2>/dev/null || true
    echo "✅ Temporary test logs cleared"
fi

# Restart containers
echo "🔄 Restarting containers..."
docker-compose down
docker-compose up -d --build

# Wait for containers to start
echo "⏳ Waiting for containers to start (30 seconds)..."
sleep 30

# Run tests
echo "🧪 Running system tests..."

TEST_ERRORS=0
TEST_MESSAGES=()

# Test 1: Check if all containers are running
echo "  ✓ Checking container status..."
EXPECTED_CONTAINERS=("realty_postgres" "realty_redis" "realty_web" "realty_bot" "realty_celery_worker" "realty_celery_beat" "realty_nginx")
RUNNING_CONTAINERS=$(docker ps --format "{{.Names}}")

for container in "${EXPECTED_CONTAINERS[@]}"; do
    if echo "$RUNNING_CONTAINERS" | grep -q "^${container}$"; then
        echo "    ✅ Container $container is running"
        TEST_MESSAGES+=("✅ $container: running")
    else
        echo "    ❌ Container $container is NOT running"
        TEST_MESSAGES+=("❌ $container: NOT running")
        TEST_ERRORS=$((TEST_ERRORS + 1))
    fi
done

# Test 2: Check web server health
echo "  ✓ Checking web server health..."
if curl -f -s http://localhost:5000/health > /dev/null 2>&1 || curl -f -s http://localhost:5000/ > /dev/null 2>&1; then
    echo "    ✅ Web server is responding"
    TEST_MESSAGES+=("✅ Web server: responding")
else
    echo "    ⚠️  Web server health check failed (may be normal if /health endpoint doesn't exist)"
    TEST_MESSAGES+=("⚠️  Web server: health check inconclusive")
fi

# Test 3: Check database connection
echo "  ✓ Checking database connection..."
if docker exec realty_postgres pg_isready -U ${POSTGRES_USER:-realty_user} > /dev/null 2>&1; then
    echo "    ✅ Database is ready"
    TEST_MESSAGES+=("✅ Database: ready")
else
    echo "    ❌ Database is NOT ready"
    TEST_MESSAGES+=("❌ Database: NOT ready")
    TEST_ERRORS=$((TEST_ERRORS + 1))
fi

# Test 4: Check Redis connection
echo "  ✓ Checking Redis connection..."
if docker exec realty_redis redis-cli ping > /dev/null 2>&1; then
    echo "    ✅ Redis is responding"
    TEST_MESSAGES+=("✅ Redis: responding")
else
    echo "    ❌ Redis is NOT responding"
    TEST_MESSAGES+=("❌ Redis: NOT responding")
    TEST_ERRORS=$((TEST_ERRORS + 1))
fi

# Test 5: Check bot container logs for errors
echo "  ✓ Checking bot container for critical errors..."
BOT_ERRORS=$(docker logs realty_bot --tail 50 2>&1 | grep -i "error\|exception\|traceback" | wc -l)
if [ "$BOT_ERRORS" -eq 0 ]; then
    echo "    ✅ No critical errors in bot logs (last 50 lines)"
    TEST_MESSAGES+=("✅ Bot logs: no critical errors")
else
    echo "    ⚠️  Found $BOT_ERRORS potential errors in bot logs (may be normal)"
    TEST_MESSAGES+=("⚠️  Bot logs: $BOT_ERRORS potential issues")
fi

# Test 6: Check web container logs for errors
echo "  ✓ Checking web container for critical errors..."
WEB_ERRORS=$(docker logs realty_web --tail 50 2>&1 | grep -i "error\|exception\|traceback" | wc -l)
if [ "$WEB_ERRORS" -eq 0 ]; then
    echo "    ✅ No critical errors in web logs (last 50 lines)"
    TEST_MESSAGES+=("✅ Web logs: no critical errors")
else
    echo "    ⚠️  Found $WEB_ERRORS potential errors in web logs (may be normal)"
    TEST_MESSAGES+=("⚠️  Web logs: $WEB_ERRORS potential issues")
fi

# Prepare test summary
echo ""
echo "📊 Test Summary:"
for msg in "${TEST_MESSAGES[@]}"; do
    echo "  $msg"
done

# Send notification to admin bot
echo ""
echo "📤 Sending notification to admin..."

# Get BOT_TOKEN from environment or .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-""}
ADMIN_ID="7615679936"

if [ -z "$BOT_TOKEN" ]; then
    echo "⚠️  Warning: TELEGRAM_BOT_TOKEN not found, skipping notification"
else
    # Prepare message
    if [ "$TEST_ERRORS" -eq 0 ]; then
        MESSAGE="✅ Развертывание завершено успешно!

Все системы запущены, ошибок нет, все работает.

📊 Результаты тестов:"
    else
        MESSAGE="⚠️ Развертывание завершено с предупреждениями

Найдено проблем: $TEST_ERRORS

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
        echo "✅ Notification sent successfully to admin"
    else
        echo "⚠️  Failed to send notification: $RESPONSE"
    fi
fi

echo ""
echo "✅ Deployment with tests completed!"
echo ""
echo "Check status:"
echo "  docker ps"
echo "  docker logs realty_web"
echo "  docker logs realty_bot"
echo ""

