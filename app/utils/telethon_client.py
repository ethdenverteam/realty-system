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

logger = logging.getLogger(__name__)

# Store active connection attempts (phone -> client)
_active_connections: Dict[str, TelegramClient] = {}


def get_session_path(phone: str) -> str:
    """Get path to session file for phone number"""
    # Normalize phone number (remove + and spaces)
    normalized_phone = phone.replace('+', '').replace(' ', '').replace('-', '')
    session_filename = f"{normalized_phone}.session"
    return os.path.join(Config.SESSIONS_FOLDER, session_filename)


async def create_client(phone: str) -> TelegramClient:
    """Create Telethon client for phone number"""
    session_path = get_session_path(phone)
    
    # Ensure sessions directory exists
    os.makedirs(Config.SESSIONS_FOLDER, exist_ok=True)
    
    if not Config.TELEGRAM_API_ID or not Config.TELEGRAM_API_HASH:
        raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be configured")
    
    client = TelegramClient(
        session_path,
        Config.TELEGRAM_API_ID,
        Config.TELEGRAM_API_HASH
    )
    
    return client


async def start_connection(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Start connection process for phone number
    Returns: (success, error_message or code_hash)
    """
    try:
        client = await create_client(phone)
        await client.connect()
        
        if not await client.is_user_authorized():
            # Send code request
            try:
                sent_code = await client.send_code_request(phone)
                code_hash = sent_code.phone_code_hash
                _active_connections[phone] = client
                return (True, code_hash)
            except PhoneNumberInvalidError:
                return (False, "Invalid phone number format")
            except Exception as e:
                logger.error(f"Error sending code: {e}")
                return (False, f"Failed to send code: {str(e)}")
        else:
            # Already authorized
            await client.disconnect()
            return (True, None)
    except Exception as e:
        logger.error(f"Error starting connection: {e}")
        return (False, f"Connection error: {str(e)}")


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
    try:
        client = await create_client(phone)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return (False, "Account not authorized. Please connect first.", None)
        
        # Send message
        sent_message = await client.send_message(int(chat_id), message)
        message_id = sent_message.id
        
        await client.disconnect()
        return (True, None, message_id)
    except Exception as e:
        logger.error(f"Error sending test message: {e}")
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

