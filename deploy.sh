#!/bin/bash
# Script for automatic deployment after git pull
#
# IMPORTANT: If you get "Permission denied" error, run:
#   chmod +x deploy.sh
# Or run with: bash deploy.sh

# Ensure script is executable (fixes issue after git reset --hard)
# This allows the script to set its own permissions
# Note: This only works if script is already executable or run with bash
chmod +x "$0" 2>/dev/null || true

set -e  # Stop on error

echo "🚀 Starting deployment..."

# Navigate to project directory
cd ~/realty-system

# Get updates
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
    > logs/test_telethon.log 2>/dev/null || true
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
echo ""

# Timer function to prevent console from closing
timer_pid=""
start_timer() {
    (
        sleep 540  # 9 minutes = 540 seconds
        echo ""
        echo "⚠️  To prevent console from closing - press any key or 'n' to cancel"
        while true; do
            read -t 1 -n 1 input
            if [ $? -eq 0 ]; then
                if [ "$input" = "n" ] || [ "$input" = "N" ]; then
                    echo "Timer cancelled."
                    return
                else
                    echo "Timer restarted for 9 minutes..."
                    start_timer
                    return
                fi
            fi
        done
    ) &
    timer_pid=$!
}

# Start the timer in background
start_timer

