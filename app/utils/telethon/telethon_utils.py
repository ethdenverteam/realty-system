"""
Telethon utilities
Логика: утилиты для работы с Telethon (run_async, helpers)
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

def run_async(coro):
    """Run async coroutine in new event loop"""
    try:
        # Try to get current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, we need to use a different approach
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists, create new one
        return asyncio.run(coro)

