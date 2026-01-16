#!/bin/bash
# Script for automatic deployment after git pull

set -e  # Stop on error

echo "🚀 Starting deployment..."

# Navigate to project directory
cd ~/realty-system

# Get updates
echo "📥 Getting updates from git..."
git pull

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

# Clear test logs (fresh start for testing)
echo "🧹 Clearing test logs for fresh testing session..."
if [ -d "logs" ]; then
    # Clear test log files (they will be recreated on container start)
    > logs/test_app.log 2>/dev/null || true
    > logs/test_errors.log 2>/dev/null || true
    > logs/test_database.log 2>/dev/null || true
    > logs/test_api.log 2>/dev/null || true
    > logs/test_celery.log 2>/dev/null || true
    > logs/test_bot.log 2>/dev/null || true
    > logs/test_bot_errors.log 2>/dev/null || true
    echo "✅ Test logs cleared (fresh start for AI analysis)"
fi

# Restart containers
echo "🔄 Restarting containers..."
docker-compose down
docker-compose up -d --build

echo "✅ Deployment completed!"
echo ""
echo "Check status:"
echo "  docker ps"
echo "  docker logs realty_web"
echo "  docker logs realty_bot"

