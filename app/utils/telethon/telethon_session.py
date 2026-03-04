"""
Telethon session management
Логика: управление сессиями Telethon, блокировки, пути к файлам
"""
import asyncio
import os
import logging
import time
import threading
from typing import Optional, Dict, List, Tuple
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PhoneNumberInvalidError,
    FloodWaitError,
    InviteHashExpiredError,
    UserAlreadyParticipantError,
    ChatAdminRequiredError,
    ChannelPrivateError,
    UsernameNotOccupiedError,
)
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import Channel, Chat, User
from app.config import Config

logger = logging.getLogger(__name__)
telethon_logger = logging.getLogger('telethon')

_active_connections: Dict[str, TelegramClient] = {}
_session_locks: Dict[str, threading.Lock] = {}
_session_locks_lock = threading.Lock()

def get_session_lock(phone: str) -> threading.Lock:
    """Get or create a lock for a specific phone number's session file"""
    with _session_locks_lock:
        if phone not in _session_locks:
            _session_locks[phone] = threading.Lock()
        return _session_locks[phone]


def get_session_path(phone: str) -> str:
    """Get path to session file for phone number"""
    # Normalize phone number (remove spaces, dashes, parentheses, but keep + for filename safety)
    # For filename, we'll use a safe version without special characters
    # IMPORTANT: Use consistent normalization - remove + but keep all digits
    normalized_phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
    # Ensure we have a valid filename (replace any remaining special chars)
    import re
    normalized_phone = re.sub(r'[^0-9]', '', normalized_phone)
    session_filename = f"{normalized_phone}.session"
    return os.path.join(Config.SESSIONS_FOLDER, session_filename)


def cleanup_connection(phone: str):
    """Clean up connection for phone number"""
    if phone in _active_connections:
        try:
            asyncio.create_task(_active_connections[phone].disconnect())
        except:
            pass
        del _active_connections[phone]


