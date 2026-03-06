"""
Telethon connection management
Логика: подключение к Telegram, валидация, верификация кода и 2FA
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
    
    ВАЖНО: Эта функция используется ТОЛЬКО для диагностики в админке.
    В боевой логике отправки сообщений мы убрали защитные проверки и всегда пробуем отправку,
    а любые проблемы Telegram видим "как есть".
    
    Функция просматривает ВСЕ диалоги аккаунта (limit=None) для поиска чата по ID.
    """
    original_id = telegram_chat_id
    try:
        # 1) Пытаемся напрямую получить сущность по тому ID/строке, который храним в БД.
        # Это даёт нам корректное поведение как для Telethon‑ID, так и для Bot API chat_id (-100...).
        target = telegram_chat_id
        if isinstance(target, str):
            try:
                # Если это числовая строка — конвертируем в int (Telethon сам разрулит формат).
                target = int(target)
            except ValueError:
                # Ненумерическое значение (username/ссылка) — пробуем как есть.
                pass

        try:
            entity = await client.get_entity(target)
            resolved_id = getattr(entity, 'id', None)
            logger.debug(
                f"validate_chat_peer: resolved telegram_chat_id={original_id} "
                f"to entity id={resolved_id}"
            )
            return True
        except (ChannelPrivateError, UsernameNotOccupiedError) as e:
            # Аккаунт не имеет доступа к чату / чат приватный
            logger.warning(
                f"validate_chat_peer: chat {original_id} is not accessible for this account: {e}"
            )
            telethon_logger.warning(
                f"validate_chat_peer: chat {original_id} is not accessible for this account: {e}"
            )
            return False
        except Exception as e:
            # Любая другая ошибка при get_entity — логируем и переходим к запасному пути.
            logger.warning(
                f"validate_chat_peer: get_entity failed for {original_id}, "
                f"falling back to dialogs scan: {e}"
            )
            telethon_logger.warning(
                f"validate_chat_peer: get_entity failed for {original_id}, "
                f"falling back to dialogs scan: {e}"
            )

        # 2) Запасной путь: просматриваем все диалоги и ищем совпадение по ID.
        # Используем limit=None, чтобы не отваливаться на аккаунтах с большим числом чатов.
        dialogs = await client.get_dialogs(limit=None)
        for dlg in dialogs:
            entity = dlg.entity
            ent_id = getattr(entity, 'id', None)
            if ent_id is None:
                continue

            try:
                if isinstance(original_id, str):
                    # В БД могли сохранить строку из Telethon (str(entity.id)).
                    if str(ent_id) == original_id:
                        logger.debug(
                            f"validate_chat_peer: matched dialog entity.id={ent_id} "
                            f"for telegram_chat_id={original_id}"
                        )
                        return True
                else:
                    if int(ent_id) == int(original_id):
                        logger.debug(
                            f"validate_chat_peer: matched dialog entity.id={ent_id} "
                            f"for telegram_chat_id={original_id}"
                        )
                return True
            except Exception as cmp_err:
                # Не даём сравнительной ошибке прервать проверку остальных диалогов
                logger.debug(
                    f"validate_chat_peer: error while comparing ids "
                    f"(entity_id={ent_id}, telegram_chat_id={original_id}): {cmp_err}"
                )
                continue

        logger.warning(
            f"validate_chat_peer: chat {original_id} not found in account dialogs; "
            f"peer considered invalid"
        )
        telethon_logger.warning(
            f"validate_chat_peer: chat {original_id} not found in account dialogs; "
            f"peer considered invalid"
        )
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


