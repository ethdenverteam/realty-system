"""
Утилиты для работы с временем (МСК)
"""
from datetime import datetime, timedelta
from bot.utils import get_moscow_time


def get_next_allowed_time_msk(now_msk: datetime = None) -> datetime:
    """
    Получить ближайшее разрешенное время для публикации (8:00-21:00 МСК)
    Если сейчас вне разрешенного времени - возвращает ближайшее разрешенное время
    Если сейчас в разрешенном времени - возвращает текущее время
    """
    if now_msk is None:
        now_msk = get_moscow_time()
    
    # Если сейчас до 8:00 - ставим на 8:00 сегодня
    if now_msk.hour < 8:
        return now_msk.replace(hour=8, minute=0, second=0, microsecond=0)
    
    # Если сейчас после 21:00 - ставим на 8:00 следующего дня
    if now_msk.hour >= 21:
        tomorrow = now_msk + timedelta(days=1)
        return tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
    
    # Если сейчас в разрешенном времени (8:00-21:00) - возвращаем текущее время
    return now_msk


def get_next_scheduled_time_for_publication(now_msk: datetime = None) -> datetime:
    """
    Получить время для публикации при попытке публикации
    Если сейчас в разрешенном времени - ставим на следующее свободное время начиная с 8 утра следующего дня
    Если сейчас вне разрешенного времени - ставим на ближайшее разрешенное время
    """
    if now_msk is None:
        now_msk = get_moscow_time()
    
    # Всегда ставим на следующий день, ближайшее свободное время начиная с 8 утра
    tomorrow = now_msk + timedelta(days=1)
    return tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)


def msk_to_utc(msk_time: datetime) -> datetime:
    """
    Конвертировать МСК время в UTC для сохранения в БД
    """
    try:
        from zoneinfo import ZoneInfo
        MOSCOW_TZ = ZoneInfo('Europe/Moscow')
        UTC_TZ = ZoneInfo('UTC')
    except ImportError:
        import pytz
        MOSCOW_TZ = pytz.timezone('Europe/Moscow')
        UTC_TZ = pytz.timezone('UTC')
    
    # Создаем datetime с МСК таймзоной
    msk_time_with_tz = msk_time.replace(tzinfo=MOSCOW_TZ)
    # Конвертируем в UTC
    utc_time = msk_time_with_tz.astimezone(UTC_TZ).replace(tzinfo=None)
    return utc_time

