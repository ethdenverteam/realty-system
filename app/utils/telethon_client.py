"""
Telethon client utilities for managing user Telegram accounts
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

# Use both loggers: app.utils.telethon_client for app logs and telethon for telethon-specific logs
logger = logging.getLogger(__name__)
telethon_logger = logging.getLogger('telethon')  # For test_telethon.log

# Store active connection attempts (phone -> client)
_active_connections: Dict[str, TelegramClient] = {}

# Lock for session file access to prevent "database is locked" errors
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


def _is_connection_error(exc: Exception) -> bool:
    """
    Heuristic to detect connection-related errors that are worth retrying.
    """
    message = str(exc).lower()
    keywords = [
        'connection', 'disconnect', 'timed out', 'timeout',
        'network is unreachable', 'failed to establish a new connection',
        'cannot connect', 'unable to connect', 'connection reset',
        'dns', 'name or service not known'
    ]
    return any(k in message for k in keywords)


async def create_client(phone: str) -> TelegramClient:
    """Create Telethon client for phone number"""
    session_path = get_session_path(phone)
    logger.debug(f"Session path for {phone}: {session_path}")
    
    # Ensure sessions directory exists
    os.makedirs(Config.SESSIONS_FOLDER, exist_ok=True)
    
    if not Config.TELEGRAM_API_ID or Config.TELEGRAM_API_ID == 0 or not Config.TELEGRAM_API_HASH:
        error_msg = f"TELEGRAM_API_ID and TELEGRAM_API_HASH must be configured. Current values: API_ID={Config.TELEGRAM_API_ID}, API_HASH={'***' if Config.TELEGRAM_API_HASH else '(empty)'}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.debug(f"Creating TelegramClient with API_ID={Config.TELEGRAM_API_ID}, API_HASH={'***' if Config.TELEGRAM_API_HASH else '(empty)'}")
    client = TelegramClient(
        session_path,
        Config.TELEGRAM_API_ID,
        Config.TELEGRAM_API_HASH
    )
    
    return client


async def validate_chat_peer(client: TelegramClient, telegram_chat_id: int) -> bool:
    """
    Проверяет, что для данного клиента существует валидный peer с указанным telegram_chat_id.
    Используется перед отправкой сообщения, чтобы избежать Invalid Peer.
    """
    try:
        # Получаем диалог/чат по ID, если не удаётся — peer невалиден
        dialogs = await client.get_dialogs(limit=200)
        for dlg in dialogs:
            entity = dlg.entity
            if hasattr(entity, 'id') and int(getattr(entity, 'id')) == int(telegram_chat_id):
                return True
        return False
    except Exception as e:
        logger.error(f"Error validating chat peer {telegram_chat_id}: {e}", exc_info=True)
        telethon_logger.error(f"Error validating chat peer {telegram_chat_id}: {e}", exc_info=True)
        return False


async def start_connection(phone: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Start connection process for phone number
    Returns: (success, error_message or code_hash, warning_message)
    """
    log_msg = f"Starting connection for phone: {phone}"
    logger.info(log_msg)
    telethon_logger.info(log_msg)
    try:
        debug_msg = f"Creating Telethon client for phone: {phone}"
        logger.debug(debug_msg)
        telethon_logger.debug(debug_msg)
        client = await create_client(phone)
        
        debug_msg = f"Connecting to Telegram servers..."
        logger.debug(debug_msg)
        telethon_logger.debug(debug_msg)
        await client.connect()
        log_msg = f"Successfully connected to Telegram servers"
        logger.info(log_msg)
        telethon_logger.info(log_msg)
        
        is_authorized = await client.is_user_authorized()
        debug_msg = f"User authorized status: {is_authorized}"
        logger.debug(debug_msg)
        telethon_logger.debug(debug_msg)
        
        if not is_authorized:
            # Send code request
            log_msg = f"Sending verification code request for phone: {phone}"
            logger.info(log_msg)
            telethon_logger.info(log_msg)
            try:
                # Try to send code - first attempt (Telegram decides the method)
                sent_code = await client.send_code_request(phone)
                code_hash = sent_code.phone_code_hash
                
                # Check if we got App type and phone_registered is None/False - try to force SMS
                code_type = getattr(sent_code, 'type', None)
                code_type_name = code_type.__class__.__name__ if code_type else 'Unknown'
                phone_registered = getattr(sent_code, 'phone_registered', None)
                
                # If we got App type and phone might not be registered, try to request SMS instead
                if code_type_name == 'SentCodeTypeApp' and (phone_registered is None or phone_registered is False):
                    logger.info(f"Attempting to request SMS code instead of App code for phone {phone}")
                    telethon_logger.info(f"Attempting to request SMS code instead of App code for phone {phone}")
                    try:
                        # Try to resend code via SMS (if Telegram allows)
                        sent_code = await client.send_code_request(phone, force_sms=True)
                        code_hash = sent_code.phone_code_hash
                        logger.info(f"Successfully requested SMS code for phone {phone}")
                        telethon_logger.info(f"Successfully requested SMS code for phone {phone}")
                    except Exception as sms_error:
                        # SMS request failed, use original App code
                        logger.warning(f"Failed to request SMS code for {phone}: {sms_error}. Using App code.")
                        telethon_logger.warning(f"Failed to request SMS code for {phone}: {sms_error}. Using App code.")
                        # sent_code already contains the App code from first request
                
                # Re-extract info after potential SMS request
                code_type = getattr(sent_code, 'type', None)
                code_type_name = code_type.__class__.__name__ if code_type else 'Unknown'
                phone_registered = getattr(sent_code, 'phone_registered', None)
                timeout = getattr(sent_code, 'timeout', None)
                next_type = getattr(sent_code, 'next_type', None)
                next_type_name = next_type.__class__.__name__ if next_type else None
                
                # Log to both loggers
                log_message = (
                    f"Verification code sent successfully for phone {phone}. "
                    f"Code hash: {code_hash[:10]}..., "
                    f"Type: {code_type_name}, "
                    f"Phone registered: {phone_registered}, "
                    f"Timeout: {timeout}s"
                )
                logger.info(log_message)
                telethon_logger.info(log_message)
                
                debug_message = (
                    f"Full sent_code response: "
                    f"type={sent_code.__class__.__name__}, "
                    f"phone_code_hash={code_hash}, "
                    f"phone_registered={phone_registered}, "
                    f"code_type={code_type_name}, "
                    f"timeout={timeout}, "
                    f"next_type={next_type_name}"
                )
                logger.debug(debug_message)
                telethon_logger.debug(debug_message)
                
                # CRITICAL: Check if code type is App (not SMS) - this means code won't come via SMS!
                if code_type_name == 'SentCodeTypeApp':
                    # If phone_registered is None or False, code might not arrive even in app!
                    if phone_registered is None or phone_registered is False:
                        critical_warning = (
                            f"🚨 КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ для номера {phone}: "
                            f"Код отправляется через ПРИЛОЖЕНИЕ (SentCodeTypeApp), "
                            f"но phone_registered={phone_registered}. "
                            f"Код НЕ ПРИДЕТ, если номер НЕ зарегистрирован в Telegram! "
                            f"Пользователь должен сначала зарегистрировать номер в приложении Telegram, "
                            f"затем открыть приложение и дождаться кода. "
                            f"Если номер уже зарегистрирован, убедитесь что приложение Telegram открыто и подключено к интернету."
                        )
                        logger.error(critical_warning)
                        telethon_logger.error(critical_warning)
                    else:
                        warning_msg = (
                            f"⚠️ ВНИМАНИЕ: Код для номера {phone} отправляется через ПРИЛОЖЕНИЕ Telegram, "
                            f"а НЕ по SMS! Код придет только в приложение Telegram на этом телефоне. "
                            f"Пользователь должен открыть приложение Telegram, чтобы получить код."
                        )
                        logger.warning(warning_msg)
                        telethon_logger.warning(warning_msg)
                elif code_type_name not in ['SentCodeTypeSms', 'SentCodeTypeApp']:
                    warning_msg = (
                        f"⚠️ Неожиданный тип кода для номера {phone}: {code_type_name}. "
                        f"Код может не прийти по SMS. Phone registered: {phone_registered}, Next type: {next_type_name}"
                    )
                    logger.warning(warning_msg)
                    telethon_logger.warning(warning_msg)
                
                # Special logging for international numbers that might have SMS delivery issues
                country_code = phone[:3] if len(phone) >= 3 else phone[:2] if len(phone) >= 2 else ''
                if country_code and country_code not in ['+7', '+1']:  # Russia and US/North America
                    info_msg = (
                        f"🌍 Международный номер: {phone} (код страны: {country_code}). "
                        f"Тип кода: {code_type_name}, Зарегистрирован: {phone_registered}. "
                        f"Если SMS не приходит, Telegram может требовать использование приложения или звонка."
                    )
                    logger.info(info_msg)
                    telethon_logger.info(info_msg)
                
                # Check if phone is not registered - this is critical for code delivery
                if phone_registered is False:
                    error_msg = (
                        f"❌ Номер телефона {phone} НЕ зарегистрирован в Telegram! "
                        f"Пользователь должен сначала зарегистрировать этот номер в приложении Telegram."
                    )
                    logger.error(error_msg)
                    telethon_logger.error(error_msg)
                
                _active_connections[phone] = client
                
                # Generate warning message if needed
                warning_message = None
                if code_type_name == 'SentCodeTypeApp' and (phone_registered is None or phone_registered is False):
                    warning_message = (
                        f"Код отправляется через приложение Telegram. "
                        f"Если номер не зарегистрирован в Telegram, код не придет. "
                        f"Убедитесь, что номер зарегистрирован в приложении Telegram и приложение открыто."
                    )
                
                return (True, code_hash, warning_message)
            except PhoneNumberInvalidError as e:
                error_msg = f"Invalid phone number format: {phone}. Error: {e}"
                logger.error(error_msg)
                telethon_logger.error(error_msg)
                return (False, "Invalid phone number format", None)
            except Exception as e:
                error_msg = f"Error sending code for phone {phone}: {e}"
                logger.error(error_msg, exc_info=True)
                telethon_logger.error(error_msg, exc_info=True)
                return (False, f"Failed to send code: {str(e)}", None)
        else:
            # Already authorized
            log_msg = f"Phone {phone} is already authorized"
            logger.info(log_msg)
            telethon_logger.info(log_msg)
            await client.disconnect()
            return (True, None, None)
    except Exception as e:
        error_msg = f"Error starting connection for phone {phone}: {e}"
        logger.error(error_msg, exc_info=True)
        telethon_logger.error(error_msg, exc_info=True)
        return (False, f"Connection error: {str(e)}", None)


async def verify_code(phone: str, code: str, code_hash: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Verify phone code
    Returns: (success, error_message, requires_2fa)
    """
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        # Ensure we have an active client; if not, try to recreate it from session
        if phone not in _active_connections:
            try:
                client = await create_client(phone)
                await client.connect()
                _active_connections[phone] = client
            except Exception as conn_err:
                logger.error(f"Error creating client for verify_code (attempt {attempt + 1}/{max_retries}) for {phone}: {conn_err}")
                if _is_connection_error(conn_err) and attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return (False, f"Connection error while verifying code: {str(conn_err)}", None)
        
        client = _active_connections[phone]
        
        try:
            try:
                await client.sign_in(phone, code, phone_code_hash=code_hash)
                # Successfully signed in
                await client.disconnect()
                del _active_connections[phone]
                return (True, None, None)
            except SessionPasswordNeededError:
                # 2FA required, keep client in _active_connections for verify_2fa
                return (True, None, "2FA_REQUIRED")
            except PhoneCodeInvalidError:
                return (False, "Invalid verification code", None)
            except Exception as e:
                logger.error(f"Error verifying code (attempt {attempt + 1}/{max_retries}) for {phone}: {e}")
                if _is_connection_error(e) and attempt < max_retries - 1:
                    # Reset client and retry on connection-related problems
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
                    if phone in _active_connections:
                        del _active_connections[phone]
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return (False, f"Verification error: {str(e)}", None)
        except Exception as e:
            logger.error(f"Unexpected error in verify_code (attempt {attempt + 1}/{max_retries}) for {phone}: {e}")
            if phone in _active_connections:
                try:
                    await _active_connections[phone].disconnect()
                except Exception:
                    pass
                del _active_connections[phone]
            if _is_connection_error(e) and attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            return (False, f"Error: {str(e)}", None)
    
    return (False, "Verification failed after multiple connection attempts. Please try again.", None)


async def verify_2fa(phone: str, password: str) -> Tuple[bool, Optional[str]]:
    """
    Verify 2FA password
    Returns: (success, error_message)
    """
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        # If connection context is lost, try to recreate client from existing session file
        if phone not in _active_connections:
            try:
                client = await create_client(phone)
                await client.connect()
                _active_connections[phone] = client
            except Exception as conn_err:
                logger.error(f"Error creating client for verify_2fa (attempt {attempt + 1}/{max_retries}) for {phone}: {conn_err}")
                if _is_connection_error(conn_err) and attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return (False, f"Connection error while verifying 2FA: {str(conn_err)}")
        
        client = _active_connections[phone]
        
        try:
            await client.sign_in(password=password)
            # Successfully signed in
            await client.disconnect()
            del _active_connections[phone]
            return (True, None)
        except Exception as e:
            logger.error(f"Error verifying 2FA (attempt {attempt + 1}/{max_retries}) for {phone}: {e}")
            if _is_connection_error(e) and attempt < max_retries - 1:
                try:
                    await client.disconnect()
                except Exception:
                    pass
                if phone in _active_connections:
                    del _active_connections[phone]
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            # Any non-connection error is treated as invalid 2FA password
            if phone in _active_connections:
                try:
                    await _active_connections[phone].disconnect()
                except Exception:
                    pass
                del _active_connections[phone]
            return (False, f"Invalid 2FA password: {str(e)}")
    
    return (False, "2FA verification failed after multiple connection attempts. Please try again.")


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


async def subscribe_to_chat(phone: str, chat_link: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Подписаться на чат/канал по ссылке
    Returns: (success, error_message, chat_info)
    chat_info содержит: telegram_chat_id, title, type
    """
    session_lock = get_session_lock(phone)
    max_retries = 3
    retry_delay = 1.0
    client = None
    
    for attempt in range(max_retries):
        try:
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
        # Check authorization
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
                    logger.warning(f"Session file existed but was not authorized for {phone} (subscribe_to_chat). Deleted session file.")
                except Exception as rm_err:
                    logger.error(f"Failed to delete unauthorized session file {session_path} for {phone}: {rm_err}")
                return (False, "Session file existed but account was not authorized. Session has been reset, please reconnect the account.", None)
            else:
                return (False, "Account not authorized. Please connect first.", None)
        
        # Parse chat link - убеждаемся что это строка
        if not isinstance(chat_link, str):
            chat_link = str(chat_link)
        chat_link = chat_link.strip()
        
        # Check if it's an invite link (https://t.me/+...)
        if chat_link.startswith('https://t.me/+') or chat_link.startswith('http://t.me/+'):
            # Extract hash from invite link
            invite_hash = chat_link.split('+')[-1]
            logger.info(f"Subscribing to chat via invite link for {phone}, hash: {invite_hash[:10]}...")
            telethon_logger.info(f"Subscribing to chat via invite link for {phone}, hash: {invite_hash[:10]}...")
            
            try:
                # Import chat invite
                result = await client(ImportChatInviteRequest(invite_hash))
                
                # Get chat info
                chat_entity = None
                if hasattr(result, 'chats') and result.chats:
                    chat_entity = result.chats[0]
                elif hasattr(result, 'chat'):
                    chat_entity = result.chat
                
                if chat_entity:
                    chat_id = str(chat_entity.id)
                    title = getattr(chat_entity, 'title', None) or f'Chat {chat_id}'
                    chat_type = 'channel' if isinstance(chat_entity, Channel) and chat_entity.broadcast else 'group'
                    
                    chat_info = {
                        'telegram_chat_id': chat_id,
                        'title': title,
                        'type': chat_type,
                    }
                    
                    logger.info(f"Successfully subscribed to chat {title} ({chat_id}) for {phone}")
                    telethon_logger.info(f"Successfully subscribed to chat {title} ({chat_id}) for {phone}")
                    await client.disconnect()
                    return (True, None, chat_info)
                else:
                    await client.disconnect()
                    return (False, "Subscribed but could not get chat info", None)
                    
            except FloodWaitError as e:
                # Flood wait error - нужно подождать
                wait_seconds = e.seconds
                logger.warning(f"FloodWaitError for {phone}: wait {wait_seconds} seconds")
                telethon_logger.warning(f"FloodWaitError for {phone}: wait {wait_seconds} seconds")
                await client.disconnect()
                return (False, f"FLOOD_WAIT:{wait_seconds}", None)
            except UserAlreadyParticipantError:
                # Уже подписан - получаем информацию о чате
                logger.info(f"User {phone} already subscribed to chat, getting chat info")
                # Пытаемся найти чат в диалогах
                try:
                    # Извлекаем username или ID из ссылки для поиска
                    # Для invite ссылок сложнее, но попробуем найти по последним диалогам
                    async for dialog in client.iter_dialogs(limit=100):
                        if dialog.is_group or dialog.is_channel:
                            entity = dialog.entity
                            chat_id = str(entity.id)
                            title = dialog.name or getattr(entity, 'title', None) or f'Chat {chat_id}'
                            chat_type = 'channel' if isinstance(entity, Channel) and entity.broadcast else 'group'
                            
                            chat_info = {
                                'telegram_chat_id': chat_id,
                                'title': title,
                                'type': chat_type,
                                'already_subscribed': True,  # Помечаем, что аккаунт уже был подписан
                            }
                            
                            await client.disconnect()
                            return (True, None, chat_info)
                except Exception as e:
                    logger.error(f"Error getting chat info after UserAlreadyParticipantError: {e}")
                    await client.disconnect()
                    return (False, "Already subscribed but could not get chat info", None)
            except InviteHashExpiredError:
                await client.disconnect()
                return (False, "Invite link has expired", None)
            except Exception as e:
                logger.error(f"Error subscribing to chat via invite link: {e}")
                telethon_logger.error(f"Error subscribing to chat via invite link: {e}")
                await client.disconnect()
                return (False, f"Error subscribing: {str(e)}", None)
        
        # Check if it's a public chat (https://t.me/username)
        elif chat_link.startswith('https://t.me/') or chat_link.startswith('http://t.me/'):
            username = chat_link.split('/')[-1].replace('@', '')
            # Skip invite links (they start with +)
            if username.startswith('+'):
                await client.disconnect()
                return (False, "Invalid chat link format. Expected https://t.me/+... or https://t.me/username", None)
            
            logger.info(f"Subscribing to public chat @{username} for {phone}")
            telethon_logger.info(f"Subscribing to public chat @{username} for {phone}")
            
            try:
                # Get entity and join
                entity = await client.get_entity(username)
                
                # Try to join if it's a channel or group
                from telethon.tl.functions.channels import JoinChannelRequest
                if isinstance(entity, Channel):
                    await client(JoinChannelRequest(entity))
                else:
                    # Для публичных групп просто получаем entity, подписка происходит автоматически при get_entity
                    # Но если нужно явно подписаться, используем JoinChannelRequest для supergroup
                    if hasattr(entity, 'access_hash'):
                        # Это supergroup, используем JoinChannelRequest
                        await client(JoinChannelRequest(entity))
                
                # Get chat info
                chat_id = str(entity.id)
                title = getattr(entity, 'title', None) or username
                chat_type = 'channel' if isinstance(entity, Channel) and entity.broadcast else 'group'
                
                chat_info = {
                    'telegram_chat_id': chat_id,
                    'title': title,
                    'type': chat_type,
                }
                
                logger.info(f"Successfully subscribed to chat {title} ({chat_id}) for {phone}")
                telethon_logger.info(f"Successfully subscribed to chat {title} ({chat_id}) for {phone}")
                await client.disconnect()
                return (True, None, chat_info)
                
            except FloodWaitError as e:
                wait_seconds = e.seconds
                logger.warning(f"FloodWaitError for {phone}: wait {wait_seconds} seconds")
                telethon_logger.warning(f"FloodWaitError for {phone}: wait {wait_seconds} seconds")
                await client.disconnect()
                return (False, f"FLOOD_WAIT:{wait_seconds}", None)
            except UserAlreadyParticipantError:
                # Уже подписан
                try:
                    entity = await client.get_entity(username)
                    chat_id = str(entity.id)
                    title = getattr(entity, 'title', None) or username
                    chat_type = 'channel' if isinstance(entity, Channel) and entity.broadcast else 'group'
                    
                    chat_info = {
                        'telegram_chat_id': chat_id,
                        'title': title,
                        'type': chat_type,
                        'already_subscribed': True,  # Помечаем, что аккаунт уже был подписан
                    }
                    
                    await client.disconnect()
                    return (True, None, chat_info)
                except Exception as e:
                    logger.error(f"Error getting chat info: {e}")
                    await client.disconnect()
                    return (False, "Already subscribed but could not get chat info", None)
            except UsernameNotOccupiedError:
                await client.disconnect()
                return (False, "Chat not found", None)
            except ChannelPrivateError:
                await client.disconnect()
                return (False, "Channel is private", None)
            except Exception as e:
                logger.error(f"Error subscribing to public chat: {e}")
                telethon_logger.error(f"Error subscribing to public chat: {e}")
                await client.disconnect()
                return (False, f"Error subscribing: {str(e)}", None)
        else:
            await client.disconnect()
            return (False, "Invalid chat link format. Expected https://t.me/+... or https://t.me/username", None)
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error subscribing to chat for {phone}: {e}")
        telethon_logger.error(f"Unexpected error subscribing to chat for {phone}: {e}")
        try:
            await client.disconnect()
        except:
            pass
        return (False, f"Unexpected error: {error_msg}", None)
    finally:
        # Ensure lock is released
        if session_lock.locked():
            try:
                session_lock.release()
            except:
                pass


# Helper function to run async code from sync context
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

