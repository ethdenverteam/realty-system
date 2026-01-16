#!/bin/bash
# Script to sync logs from server to local project
# Usage: ./sync_logs.sh [server_user@server_host]

set -e

# Configuration
SERVER_USER="${1:-root}"
SERVER_HOST="${2:-msk-1-vm-vgtr}"
SERVER_PATH="${3:-~/realty-system/logs}"
LOCAL_PATH="logs_server"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔄 Syncing logs from server...${NC}"
echo "Server: ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}"
echo "Local: ${LOCAL_PATH}/"
echo ""

# Create local directory if it doesn't exist
mkdir -p "${LOCAL_PATH}"

# Sync logs using rsync (preferred) or scp
if command -v rsync &> /dev/null; then
    echo -e "${YELLOW}Using rsync...${NC}"
    rsync -avz --progress \
        --exclude='*.log.*' \
        --include='*.log' \
        "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/" \
        "${LOCAL_PATH}/"
else
    echo -e "${YELLOW}Using scp (rsync not found)...${NC}"
    # Fallback to scp
    scp "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/*.log" "${LOCAL_PATH}/"
fi

# Create .gitignore entry if doesn't exist
if ! grep -q "^logs_server/" .gitignore 2>/dev/null; then
    echo "logs_server/" >> .gitignore
    echo -e "${GREEN}✅ Added logs_server/ to .gitignore${NC}"
fi

echo ""
echo -e "${GREEN}✅ Logs synced successfully!${NC}"
echo ""
echo "Logs are available in: ${LOCAL_PATH}/"
echo ""
echo "Files:"
ls -lh "${LOCAL_PATH}/" 2>/dev/null || echo "No log files found"

