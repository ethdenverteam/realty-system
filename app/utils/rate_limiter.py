"""
Rate limiter for Telethon to prevent account blocking
Strict limits: 1 message per minute, 60 messages per hour
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict
import threading

# Global rate limiter state
_rate_limiter_lock = threading.Lock()
_message_times: Dict[str, List[float]] = defaultdict(list)  # phone -> list of message timestamps
_rate_limit_enabled_cache: Dict[str, bool] = {'enabled': True}
_rate_limit_last_checked: Dict[str, float] = {'ts': 0.0}
_RATE_LIMIT_CACHE_TTL_SECONDS = 30.0


def _is_rate_limit_enabled() -> bool:
    """
    Глобальный переключатель лимита отправки сообщений.

    Источник правды — SystemSetting с key='account_rate_limit', value_json={'enabled': bool}.
    Если настройка отсутствует или недоступна, по умолчанию лимит ВКЛЮЧЕН (безопасный режим).
    """
    import time

    now = time.time()
    # Быстрый путь: используем кэш, чтобы не бить в БД на каждый вызов
    if now - _rate_limit_last_checked['ts'] < _RATE_LIMIT_CACHE_TTL_SECONDS:
        return _rate_limit_enabled_cache['enabled']

    try:
        from app.database import db
        from app.models.system_setting import SystemSetting

        setting = db.session.query(SystemSetting).filter_by(key='account_rate_limit').first()
        enabled = True
        if setting and isinstance(setting.value_json, dict):
            enabled = bool(setting.value_json.get('enabled', True))

        _rate_limit_enabled_cache['enabled'] = enabled
        _rate_limit_last_checked['ts'] = now
        return enabled
    except Exception:
        # При любых проблемах с БД/моделями возвращаем безопасное значение (лимит включен)
        _rate_limit_enabled_cache['enabled'] = True
        _rate_limit_last_checked['ts'] = now
        return True


def can_send_message(phone: str) -> tuple[bool, float]:
    """
    Check if we can send a message for this phone number
    Returns: (can_send, wait_seconds)
    """
    with _rate_limiter_lock:
        now = time.time()
        times = _message_times[phone]
        
        # Remove old timestamps (older than 1 hour)
        one_hour_ago = now - 3600
        times[:] = [t for t in times if t > one_hour_ago]
        
        # Check hourly limit (60 messages per hour)
        if len(times) >= 60:
            # Find the oldest message in the last hour
            oldest_in_hour = min(times) if times else now
            wait_seconds = 3600 - (now - oldest_in_hour)
            if wait_seconds > 0:
                return (False, wait_seconds)
        
        # Check per-minute limit (1 message per minute)
        if times:
            last_message_time = max(times)
            time_since_last = now - last_message_time
            if time_since_last < 60:
                wait_seconds = 60 - time_since_last
                return (False, wait_seconds)
        
        return (True, 0.0)


def record_message_sent(phone: str):
    """Record that a message was sent"""
    with _rate_limiter_lock:
        now = time.time()
        _message_times[phone].append(now)
        
        # Clean up old entries (keep only last hour)
        one_hour_ago = now - 3600
        _message_times[phone] = [t for t in _message_times[phone] if t > one_hour_ago]


def wait_if_needed(phone: str) -> float:
    """
    Wait if needed before sending message
    Returns: actual wait time in seconds
    """
    can_send, wait_seconds = can_send_message(phone)
    if not can_send and wait_seconds > 0:
        time.sleep(wait_seconds)
        return wait_seconds
    return 0.0


def get_rate_limit_status(phone: str) -> dict:
    """
    Get current rate limit status for phone.

    Если глобальный переключатель лимита выключен (SystemSetting.account_rate_limit.enabled = False),
    функция всегда возвращает can_send=True и wait_seconds=0, не учитывая локальное состояние.
    """
    with _rate_limiter_lock:
        # Глобальное отключение лимита: используем только реальные лимиты Telegram
        if not _is_rate_limit_enabled():
            return {
                'can_send': True,
                'wait_seconds': 0.0,
                'messages_in_hour': 0,
                'messages_remaining': 60,
                'next_available': None,
                'enabled': False,
            }

        now = time.time()
        times = _message_times[phone]
        
        # Remove old timestamps
        one_hour_ago = now - 3600
        times[:] = [t for t in times if t > one_hour_ago]
        
        messages_in_hour = len(times)
        can_send, wait_seconds = can_send_message(phone)
        
        # Calculate time until next available slot
        next_available = None
        if times:
            last_message_time = max(times)
            time_since_last = now - last_message_time
            if time_since_last < 60:
                next_available = datetime.utcnow() + timedelta(seconds=60 - time_since_last)
        
        return {
            'can_send': can_send,
            'wait_seconds': wait_seconds,
            'messages_in_hour': messages_in_hour,
            'messages_remaining': 60 - messages_in_hour,
            'next_available': next_available.isoformat() if next_available else None,
            'enabled': True,
        }

