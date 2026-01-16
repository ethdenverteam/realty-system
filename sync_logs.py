#!/usr/bin/env python3
"""
Python script to sync logs from server to local project
Works on both Windows and Linux
Usage: python sync_logs.py [server_user] [server_host] [server_path]
"""

import os
import sys
import subprocess
from pathlib import Path

# Configuration
DEFAULT_SERVER_USER = "root"
DEFAULT_SERVER_HOST = "msk-1-vm-vgtr"  # Update this with your server
DEFAULT_SERVER_PATH = "~/realty-system/logs"
LOCAL_PATH = "logs_server"


def run_command(cmd, shell=False):
    """Run command and return success status"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"❌ Error running command: {e}", file=sys.stderr)
        return False


def sync_with_scp(server_user, server_host, server_path):
    """Sync logs using scp"""
    print(f"📥 Syncing logs using scp...")
    
    # Create local directory
    Path(LOCAL_PATH).mkdir(exist_ok=True)
    
    # Check if we're on Windows (use wsl scp if available)
    is_windows = sys.platform == "win32"
    
    if is_windows:
        # Try using wsl scp
        wsl_cmd = ["wsl", "scp", f"{server_user}@{server_host}:{server_path}/*.log", f"{LOCAL_PATH}/"]
        if run_command(wsl_cmd):
            return True
        
        # Fallback to native scp if OpenSSH is installed
        scp_cmd = ["scp", f"{server_user}@{server_host}:{server_path}/*.log", f"{LOCAL_PATH}/"]
        return run_command(scp_cmd)
    else:
        # Linux/Mac - use native scp
        scp_cmd = ["scp", f"{server_user}@{server_host}:{server_path}/*.log", f"{LOCAL_PATH}/"]
        return run_command(scp_cmd)


def sync_with_rsync(server_user, server_host, server_path):
    """Sync logs using rsync (preferred)"""
    print(f"📥 Syncing logs using rsync...")
    
    # Create local directory
    Path(LOCAL_PATH).mkdir(exist_ok=True)
    
    is_windows = sys.platform == "win32"
    
    rsync_cmd = [
        "rsync", "-avz", "--progress",
        "--exclude=*.log.*",
        "--include=*.log",
        f"{server_user}@{server_host}:{server_path}/",
        f"{LOCAL_PATH}/"
    ]
    
    if is_windows:
        # Try wsl rsync first
        wsl_cmd = ["wsl"] + rsync_cmd
        if run_command(wsl_cmd):
            return True
        
        # Fallback to scp if rsync not available
        print("⚠️  rsync not found, falling back to scp...")
        return sync_with_scp(server_user, server_host, server_path)
    else:
        return run_command(rsync_cmd)


def update_gitignore():
    """Add logs_server/ to .gitignore if not present"""
    gitignore_path = Path(".gitignore")
    
    if not gitignore_path.exists():
        gitignore_path.write_text("logs_server/\n")
        print("✅ Created .gitignore with logs_server/")
        return
    
    content = gitignore_path.read_text()
    if "logs_server/" not in content:
        gitignore_path.write_text(content + "\n# Synced logs from server\nlogs_server/\n")
        print("✅ Added logs_server/ to .gitignore")


def main():
    # Get arguments or use defaults
    server_user = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERVER_USER
    server_host = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SERVER_HOST
    server_path = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_SERVER_PATH
    
    print(f"🔄 Syncing logs from server...")
    print(f"Server: {server_user}@{server_host}:{server_path}")
    print(f"Local: {LOCAL_PATH}/")
    print()
    
    # Try rsync first, fallback to scp
    if sync_with_rsync(server_user, server_host, server_path):
        print()
        print("✅ Logs synced successfully!")
    elif sync_with_scp(server_user, server_host, server_path):
        print()
        print("✅ Logs synced successfully!")
    else:
        print("❌ Failed to sync logs. Please check:")
        print("   1. SSH access to server is configured")
        print("   2. Server path is correct")
        print("   3. rsync or scp is installed")
        sys.exit(1)
    
    # Update .gitignore
    update_gitignore()
    
    # List synced files
    print()
    print(f"Logs are available in: {LOCAL_PATH}/")
    print()
    print("Files:")
    log_dir = Path(LOCAL_PATH)
    if log_dir.exists():
        for log_file in sorted(log_dir.glob("*.log")):
            size = log_file.stat().st_size
            size_mb = size / (1024 * 1024)
            print(f"  - {log_file.name} ({size_mb:.2f} MB)")
    else:
        print("  No log files found")


if __name__ == "__main__":
    main()

