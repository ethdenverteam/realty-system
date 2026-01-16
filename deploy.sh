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

