"""
Telethon client utilities package
Логика: объединение всех Telethon утилит для импорта
"""
# Импортируем все функции для обратной совместимости
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
    _is_connection_error,
)
from app.utils.telethon.telethon_chats import (
    get_chats,
    subscribe_to_chat,
)
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
    '_is_connection_error',
    'get_chats',
    'subscribe_to_chat',
    'send_test_message',
    'send_object_message',
    'run_async',
]

