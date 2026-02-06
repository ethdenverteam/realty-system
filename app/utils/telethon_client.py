"""
Telethon client utilities for managing user Telegram accounts
"""
import asyncio
import os
import logging
from typing import Optional, Dict, List, Tuple
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError
from telethon.tl.types import Channel, Chat, User
from app.config import Config

# Use both loggers: app.utils.telethon_client for app logs and telethon for telethon-specific logs
logger = logging.getLogger(__name__)
telethon_logger = logging.getLogger('telethon')  # For test_telethon.log

# Store active connection attempts (phone -> client)
_active_connections: Dict[str, TelegramClient] = {}


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
    if phone not in _active_connections:
        return (False, "Connection not found. Please start connection again.", None)
    
    client = _active_connections[phone]
    
    try:
        try:
            await client.sign_in(phone, code, phone_code_hash=code_hash)
            # Successfully signed in
            await client.disconnect()
            del _active_connections[phone]
            return (True, None, None)
        except SessionPasswordNeededError:
            # 2FA required
            return (True, None, "2FA_REQUIRED")
        except PhoneCodeInvalidError:
            return (False, "Invalid verification code", None)
        except Exception as e:
            logger.error(f"Error verifying code: {e}")
            return (False, f"Verification error: {str(e)}", None)
    except Exception as e:
        logger.error(f"Error in verify_code: {e}")
        if phone in _active_connections:
            await _active_connections[phone].disconnect()
            del _active_connections[phone]
        return (False, f"Error: {str(e)}", None)


async def verify_2fa(phone: str, password: str) -> Tuple[bool, Optional[str]]:
    """
    Verify 2FA password
    Returns: (success, error_message)
    """
    if phone not in _active_connections:
        return (False, "Connection not found. Please start connection again.")
    
    client = _active_connections[phone]
    
    try:
        await client.sign_in(password=password)
        # Successfully signed in
        await client.disconnect()
        del _active_connections[phone]
        return (True, None)
    except Exception as e:
        logger.error(f"Error verifying 2FA: {e}")
        if phone in _active_connections:
            await _active_connections[phone].disconnect()
            del _active_connections[phone]
        return (False, f"Invalid 2FA password: {str(e)}")


async def get_chats(phone: str) -> Tuple[bool, Optional[List[Dict]], Optional[str]]:
    """
    Get list of chats from Telegram account
    Returns: (success, chats_list, error_message)
    """
    try:
        client = await create_client(phone)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
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
        logger.error(f"Error getting chats: {e}")
        return (False, None, f"Error loading chats: {str(e)}")


async def send_test_message(phone: str, chat_id: str, message: str = "Тестовое сообщение") -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Send test message from Telegram account
    Returns: (success, error_message, message_id)
    """
    from app.utils.rate_limiter import wait_if_needed, record_message_sent
    
    try:
        # Apply rate limiting
        wait_if_needed(phone)
        
        client = await create_client(phone)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return (False, "Account not authorized. Please connect first.", None)
        
        # Send message
        sent_message = await client.send_message(int(chat_id), message)
        message_id = sent_message.id
        
        # Record message sent for rate limiting
        record_message_sent(phone)
        
        await client.disconnect()
        return (True, None, message_id)
    except Exception as e:
        logger.error(f"Error sending test message: {e}")
        try:
            await client.disconnect()
        except:
            pass
        return (False, f"Error sending message: {str(e)}", None)


async def send_object_message(phone: str, chat_id: str, message_text: str, photos: Optional[List[str]] = None) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Send object publication message from Telegram account
    Returns: (success, error_message, message_id)
    """
    from app.utils.rate_limiter import wait_if_needed, record_message_sent
    import os
    from app.config import Config
    
    try:
        # Apply rate limiting
        wait_if_needed(phone)
        
        client = await create_client(phone)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return (False, "Account not authorized. Please connect first.", None)
        
        # Send message with photos if available
        if photos and len(photos) > 0:
            # Prepare photo files
            photo_files = []
            base_dir = os.path.dirname(os.path.dirname(__file__))
            for photo_path in photos[:10]:  # Telegram allows max 10 photos
                # Handle both relative and absolute paths
                if photo_path.startswith('/'):
                    full_path = os.path.join(base_dir, photo_path.lstrip('/'))
                elif photo_path.startswith('uploads/'):
                    full_path = os.path.join(base_dir, photo_path)
                else:
                    full_path = os.path.join(base_dir, photo_path)
                
                if os.path.exists(full_path):
                    photo_files.append(full_path)
                else:
                    logger.warning(f"Photo file not found: {full_path} (original path: {photo_path})")
            
            if photo_files:
                # Send as media group or single photo
                if len(photo_files) > 1:
                    # Send as media group
                    from telethon.tl.types import InputMediaUploadedPhoto
                    media = []
                    for photo_file in photo_files:
                        uploaded_file = await client.upload_file(photo_file)
                        media.append(InputMediaUploadedPhoto(uploaded_file))
                    sent_messages = await client.send_file(int(chat_id), media, caption=message_text, parse_mode='html')
                    message_id = sent_messages[0].id if isinstance(sent_messages, list) else sent_messages.id
                else:
                    # Send single photo
                    sent_message = await client.send_file(int(chat_id), photo_files[0], caption=message_text, parse_mode='html')
                    message_id = sent_message.id
            else:
                # No valid photos, send text only
                sent_message = await client.send_message(int(chat_id), message_text, parse_mode='html')
                message_id = sent_message.id
        else:
            # Send text only
            sent_message = await client.send_message(int(chat_id), message_text, parse_mode='html')
            message_id = sent_message.id
        
        # Record message sent for rate limiting
        record_message_sent(phone)
        
        await client.disconnect()
        return (True, None, message_id)
    except Exception as e:
        logger.error(f"Error sending object message: {e}")
        try:
            await client.disconnect()
        except:
            pass
        return (False, f"Error sending message: {str(e)}", None)


def cleanup_connection(phone: str):
    """Clean up connection for phone number"""
    if phone in _active_connections:
        try:
            asyncio.create_task(_active_connections[phone].disconnect())
        except:
            pass
        del _active_connections[phone]


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

