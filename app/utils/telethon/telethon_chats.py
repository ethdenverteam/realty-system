"""
Telethon chats management
Логика: получение списка чатов, подписка на чаты
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

from app.utils.telethon.telethon_session import get_session_lock, get_session_path
from app.utils.telethon.telethon_connection import create_client

async def get_chats(phone: str) -> Tuple[bool, Optional[List[Dict]], Optional[str]]:
    """
    Get list of chats from Telegram account
    Returns: (success, chats_list, error_message)
    """
    session_lock = get_session_lock(phone)
    max_retries = 3
    retry_delay = 1.0
    client = None
    
    for attempt in range(max_retries):
        try:
            # Acquire lock before accessing session file
            if session_lock.acquire(timeout=10):
                try:
                    client = await create_client(phone)
                    await client.connect()
                    break
                except Exception as lock_error:
                    if "database is locked" in str(lock_error).lower() or "locked" in str(lock_error).lower():
                        if attempt < max_retries - 1:
                            logger.warning(f"Session file locked for {phone}, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            return (False, None, f"Session file is locked. Another process is using this account. Please wait and try again.")
                    else:
                        raise
                finally:
                    if session_lock.locked():
                        session_lock.release()
            else:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return (False, None, "Session file is locked by another process. Please try again in a few seconds.")
        except Exception as e:
            if "database is locked" in str(e).lower() or "locked" in str(e).lower():
                if attempt < max_retries - 1:
                    logger.warning(f"Session file locked for {phone}, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return (False, None, f"Session file is locked. Another process is using this account. Please wait and try again.")
            else:
                raise
    
    if client is None:
        return (False, None, "Failed to create client after retries")
    
    try:
        # Check authorization with better error handling
        try:
            is_authorized = await client.is_user_authorized()
        except Exception as auth_error:
            logger.error(f"Error checking authorization for {phone}: {auth_error}")
            await client.disconnect()
            return (False, None, f"Authorization check failed: {str(auth_error)}. Please reconnect the account.")
        
        if not is_authorized:
            await client.disconnect()
            # Check if session file exists
            session_path = get_session_path(phone)
            if os.path.exists(session_path):
                # Session exists but is not authorized – most likely stale/bитая сессия после перезапуска/смены API.
                # Автоматически удаляем файл, чтобы не заставлять пользователя разбираться вручную.
                try:
                    os.remove(session_path)
                    logger.warning(f"Session file existed but was not authorized for {phone}. Deleted session file to force clean reconnect.")
                except Exception as rm_err:
                    logger.error(f"Failed to delete unauthorized session file {session_path} for {phone}: {rm_err}")
                return (False, None, "Session file existed but account was not authorized. Session has been reset, please reconnect the account.")
            else:
                return (False, None, "Account not authorized. Please connect first.")
        
        chats = []
        async for dialog in client.iter_dialogs():
            # Only include groups, supergroups, and channels where user can send messages
            if dialog.is_group or dialog.is_channel:
                entity = dialog.entity
                
                # Check if user can send messages
                try:
                    # For channels, check if user is admin or can post
                    if isinstance(entity, Channel):
                        if entity.broadcast:
                            # Channel - check if user can post
                            if hasattr(entity, 'admin_rights') or hasattr(entity, 'default_banned_rights'):
                                # Try to get full channel info
                                try:
                                    full_channel = await client.get_entity(entity.id)
                                    if hasattr(full_channel, 'default_banned_rights'):
                                        if full_channel.default_banned_rights.send_messages:
                                            continue  # Cannot send messages
                                except:
                                    pass
                        else:
                            # Supergroup
                            pass
                    
                    # Get members count safely
                    members_count = 0
                    try:
                        if hasattr(entity, 'participants_count'):
                            members_count = entity.participants_count or 0
                        elif isinstance(entity, Channel):
                            # Try to get full info for channels
                            try:
                                full_entity = await client.get_entity(entity.id)
                                if hasattr(full_entity, 'participants_count'):
                                    members_count = full_entity.participants_count or 0
                            except:
                                pass
                    except:
                        pass
                    
                    chat_info = {
                        'id': str(entity.id),
                        'title': dialog.name,
                        'type': 'channel' if isinstance(entity, Channel) and entity.broadcast else 'supergroup' if isinstance(entity, Channel) else 'group',
                        'username': getattr(entity, 'username', None),
                        'members_count': members_count,
                    }
                    chats.append(chat_info)
                except Exception as e:
                    logger.warning(f"Error processing chat {dialog.name}: {e}")
                    continue
        
        await client.disconnect()
        return (True, chats, None)
    except Exception as e:
        error_msg = str(e)
        if "database is locked" in error_msg.lower() or "locked" in error_msg.lower():
            logger.error(f"Database locked error getting chats for {phone}: {e}")
            try:
                await client.disconnect()
            except:
                pass
            return (False, None, "Session file is locked by another process. Please wait a few seconds and try again.")
        logger.error(f"Error getting chats: {e}")
        try:
            await client.disconnect()
        except:
            pass
        return (False, None, f"Error loading chats: {str(e)}")
    finally:
        # Ensure lock is released
        if session_lock.locked():
            try:
                session_lock.release()
            except:
                pass


async def send_test_message(phone: str, chat_id: str, message: str = "Тестовое сообщение") -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Send test message from Telegram account
    Returns: (success, error_message, message_id)
    """
    from app.utils.rate_limiter import wait_if_needed, record_message_sent, can_send_message
    
    # Check rate limit first and return detailed error if needed
    can_send, wait_seconds = can_send_message(phone)
    if not can_send:
        minutes = int(wait_seconds // 60)
        seconds = int(wait_seconds % 60)
        if minutes > 0:
            wait_msg = f"{minutes} мин {seconds} сек"
        else:
            wait_msg = f"{seconds} сек"
        return (False, f"Превышен лимит отправки сообщений. В эту минуту уже было отправлено сообщение. Подождите {wait_msg} перед следующей отправкой.", None)
    
    session_lock = get_session_lock(phone)
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # Acquire lock before accessing session file
            if session_lock.acquire(timeout=10):
                try:
                    # Apply rate limiting
                    wait_if_needed(phone)
                    
                    client = await create_client(phone)
                    await client.connect()
                    break
                finally:
                    session_lock.release()
            else:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return (False, "Session file is locked by another process. Please try again in a few seconds.", None)
        except Exception as lock_error:
            if "database is locked" in str(lock_error).lower() or "locked" in str(lock_error).lower():
                if attempt < max_retries - 1:
                    logger.warning(f"Session file locked for {phone}, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return (False, "Session file is locked. Another process is using this account. Please wait and try again.", None)
            else:
                raise
    
    try:
        # Check authorization with better error handling
        try:
            is_authorized = await client.is_user_authorized()
        except Exception as auth_error:
            logger.error(f"Error checking authorization for {phone}: {auth_error}")
            await client.disconnect()
            return (False, f"Authorization check failed: {str(auth_error)}. Please reconnect the account.", None)
        
        if not is_authorized:
            await client.disconnect()
            session_path = get_session_path(phone)
            if os.path.exists(session_path):
                try:
                    os.remove(session_path)
                    logger.warning(f"Session file existed but was not authorized for {phone} (send_test_message). Deleted session file to force clean reconnect.")
                except Exception as rm_err:
                    logger.error(f"Failed to delete unauthorized session file {session_path} for {phone} (send_test_message): {rm_err}")
                return (False, "Session file existed but account was not authorized. Session has been reset, please reconnect the account.", None)
            else:
                return (False, "Account not authorized. Please connect first.", None)
        
        # Send message
        sent_message = await client.send_message(int(chat_id), message)
        message_id = sent_message.id
        
        # Record message sent for rate limiting
        record_message_sent(phone)
        
        await client.disconnect()
        return (True, None, message_id)
    except Exception as e:
        error_msg = str(e)
        if "database is locked" in error_msg.lower() or "locked" in error_msg.lower():
            logger.error(f"Database locked error sending test message for {phone}: {e}")
            try:
                await client.disconnect()
            except:
                pass
            return (False, "Session file is locked by another process. Please wait a few seconds and try again.", None)
        logger.error(f"Error sending test message: {e}")
        try:
            await client.disconnect()
        except:
            pass
        return (False, f"Error sending message: {str(e)}", None)
    finally:
        # Ensure lock is released
        if session_lock.locked():
            try:
                session_lock.release()
            except:
                pass


async def send_object_message(phone: str, chat_id: str, message_text: str, photos: Optional[List[str]] = None) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Send object publication message from Telegram account
    Returns: (success, error_message, message_id)
    """
    from app.utils.rate_limiter import wait_if_needed, record_message_sent, can_send_message
    import os
    from app.config import Config
    
    # Check rate limit first and return detailed error if needed
    can_send, wait_seconds = can_send_message(phone)
    if not can_send:
        minutes = int(wait_seconds // 60)
        seconds = int(wait_seconds % 60)
        if minutes > 0:
            wait_msg = f"{minutes} мин {seconds} сек"
        else:
            wait_msg = f"{seconds} сек"
        return (False, f"Превышен лимит отправки сообщений. В эту минуту уже было отправлено сообщение. Подождите {wait_msg} перед следующей отправкой.", None)
    
    session_lock = get_session_lock(phone)
    max_retries = 3
    retry_delay = 1.0
    client = None
    
    for attempt in range(max_retries):
        try:
            # Acquire lock before accessing session file
            if session_lock.acquire(timeout=10):
                try:
                    # Apply rate limiting
                    wait_if_needed(phone)
                    
                    client = await create_client(phone)
                    await client.connect()
                    break
                except Exception as lock_error:
                    if "database is locked" in str(lock_error).lower() or "locked" in str(lock_error).lower():
                        if attempt < max_retries - 1:
                            logger.warning(f"Session file locked for {phone}, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            return (False, "Session file is locked. Another process is using this account. Please wait and try again.", None)
                    else:
                        raise
                finally:
                    if session_lock.locked():
                        session_lock.release()
            else:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return (False, "Session file is locked by another process. Please try again in a few seconds.", None)
        except Exception as e:
            if "database is locked" in str(e).lower() or "locked" in str(e).lower():
                if attempt < max_retries - 1:
                    logger.warning(f"Session file locked for {phone}, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return (False, "Session file is locked. Another process is using this account. Please wait and try again.", None)
            else:
                raise
    
    if client is None:
        return (False, "Failed to create client after retries", None)
    
    try:
        # Check authorization with better error handling
        try:
            is_authorized = await client.is_user_authorized()
        except Exception as auth_error:
            logger.error(f"Error checking authorization for {phone}: {auth_error}")
            await client.disconnect()
            return (False, f"Authorization check failed: {str(auth_error)}. Please reconnect the account.", None)
        
        if not is_authorized:
            await client.disconnect()
            session_path = get_session_path(phone)
            if os.path.exists(session_path):
                try:
                    os.remove(session_path)
                    logger.warning(f"Session file existed but was not authorized for {phone} (send_object_message). Deleted session file to force clean reconnect.")
                except Exception as rm_err:
                    logger.error(f"Failed to delete unauthorized session file {session_path} for {phone} (send_object_message): {rm_err}")
                return (False, "Session file existed but account was not authorized. Session has been reset, please reconnect the account.", None)
            else:
                return (False, "Account not authorized. Please connect first.", None)
        
        # Перед отправкой проверяем, что peer валиден для данного клиента
        try:
            is_valid_peer = await validate_chat_peer(client, int(chat_id))
        except Exception as peer_check_error:
            logger.error(f"Error while validating peer for chat_id={chat_id}: {peer_check_error}", exc_info=True)
            is_valid_peer = False

        if not is_valid_peer:
            await client.disconnect()
            return (False, "Выбранный чат недоступен для этого аккаунта. Проверьте, что аккаунт состоит в чате и чат активен.", None)

        # Send message with photo if available - всегда отправляем фото если оно есть
        if photos and len(photos) > 0:
            # Берем первое фото (только одно фото разрешено)
            photo_path = photos[0]
            
            # Если это словарь с путем, извлекаем путь
            if isinstance(photo_path, dict):
                photo_path = photo_path.get('path', '')
            
            # Подготавливаем путь к файлу
            base_dir = os.path.dirname(os.path.dirname(__file__))
            if photo_path.startswith('/'):
                full_path = os.path.join(base_dir, photo_path.lstrip('/'))
            elif photo_path.startswith('uploads/'):
                full_path = os.path.join(base_dir, photo_path)
            else:
                full_path = os.path.join(base_dir, photo_path)
            
            if os.path.exists(full_path):
                # Отправляем одно фото
                sent_message = await client.send_file(int(chat_id), full_path, caption=message_text, parse_mode='html')
                message_id = sent_message.id
            else:
                logger.warning(f"Photo file not found: {full_path} (original path: {photo_path}), sending text only")
                # Если файл не найден, отправляем только текст
                sent_message = await client.send_message(int(chat_id), message_text, parse_mode='html')
                message_id = sent_message.id
        else:
            # Если фото нет - отправляем только текст
            sent_message = await client.send_message(int(chat_id), message_text, parse_mode='html')
            message_id = sent_message.id
        
        # Record message sent for rate limiting
        record_message_sent(phone)
        
        await client.disconnect()
        return (True, None, message_id)
    except Exception as e:
        error_msg = str(e)
        if "database is locked" in error_msg.lower() or "locked" in error_msg.lower():
            logger.error(f"Database locked error sending object message for {phone}: {e}")
            try:
                await client.disconnect()
            except:
                pass
            return (False, "Session file is locked by another process. Please wait a few seconds and try again.", None)
        logger.error(f"Error sending object message: {e}")
        try:
            await client.disconnect()
        except:
            pass
        return (False, f"Error sending message: {str(e)}", None)
    finally:
        # Ensure lock is released
        if session_lock.locked():
            try:
                session_lock.release()
            except:
                pass


def cleanup_connection(phone: str):
    """Clean up connection for phone number"""
    if phone in _active_connections:
        try:
            asyncio.create_task(_active_connections[phone].disconnect())
        except:
            pass
        del _active_connections[phone]


