"""
Telethon client module - unified interface for all Telethon operations
Логика: единая точка входа для всех операций с Telethon, экспортирует функции из модулей telethon/
"""
# Импортируем все функции из модулей telethon для обратной совместимости
from app.utils.telethon.telethon_session import (
    get_session_lock,
    get_session_path,
    cleanup_connection,
)
from app.utils.telethon.telethon_connection import (
    create_client,
    start_connection,
    verify_code,
    verify_2fa,
    validate_chat_peer,
)
from app.utils.telethon.telethon_chats import (
    get_chats,
)

# Функция subscribe_to_chat пока не реализована в модулях telethon
# Временная заглушка для обратной совместимости
async def subscribe_to_chat(phone: str, chat_link: str):
    """
    Subscribe to a chat by invite link
    TODO: Implement this function in telethon_chats.py
    """
    raise NotImplementedError("subscribe_to_chat is not yet implemented. Please implement it in app/utils/telethon/telethon_chats.py")
from app.utils.telethon.telethon_messages import (
    send_test_message,
    send_object_message,
)
from app.utils.telethon.telethon_utils import (
    run_async,
)

__all__ = [
    'get_session_lock',
    'get_session_path',
    'cleanup_connection',
    'create_client',
    'start_connection',
    'verify_code',
    'verify_2fa',
    'validate_chat_peer',
    'get_chats',
    'subscribe_to_chat',
    'send_test_message',
    'send_object_message',
    'run_async',
]

