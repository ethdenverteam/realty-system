#!/bin/bash
# Lightweight script to restart all systems for stability testing
#
# IMPORTANT: If you get "Permission denied" error, run:
#   chmod +x restart.sh
# Or run with: bash restart.sh

# Ensure script is executable
chmod +x "$0" 2>/dev/null || true

set -e  # Stop on error

echo "🔄 Starting system restart..."

# Navigate to project directory
cd ~/realty-system

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

echo "✅ System restart completed!"
echo ""
echo "Check status:"
echo "  docker ps"
echo "  docker logs realty_web"
echo "  docker logs realty_bot"
echo ""

