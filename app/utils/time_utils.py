"""
Утилиты для работы с временем (МСК)
Использует глобальную переменную SYSTEM_TIMEZONE из app.config
"""
from datetime import datetime, timedelta
from app.config import SYSTEM_TIMEZONE, AUTOPUBLISH_START_HOUR, AUTOPUBLISH_END_HOUR


def get_moscow_time() -> datetime:
    """
    Получить текущее время в системном часовом поясе (МСК)
    Использует глобальную переменную SYSTEM_TIMEZONE из app.config
    """
    try:
        from zoneinfo import ZoneInfo
        SYSTEM_TZ = ZoneInfo(SYSTEM_TIMEZONE)
    except ImportError:
        import pytz
        SYSTEM_TZ = pytz.timezone(SYSTEM_TIMEZONE)
    
    return datetime.now(SYSTEM_TZ)


def get_next_allowed_time_msk(now_msk: datetime = None) -> datetime:
    """
    Получить ближайшее разрешенное время для публикации (8:00-22:00 МСК)
    Использует глобальные константы AUTOPUBLISH_START_HOUR и AUTOPUBLISH_END_HOUR из app.config
    Если сейчас вне разрешенного времени - возвращает ближайшее разрешенное время
    Если сейчас в разрешенном времени - возвращает текущее время
    """
    if now_msk is None:
        now_msk = get_moscow_time()
    
    # Если сейчас до начала рабочего времени - ставим на начало сегодня
    if now_msk.hour < AUTOPUBLISH_START_HOUR:
        return now_msk.replace(hour=AUTOPUBLISH_START_HOUR, minute=0, second=0, microsecond=0)
    
    # Если сейчас после конца рабочего времени - ставим на начало следующего дня
    if now_msk.hour >= AUTOPUBLISH_END_HOUR:
        tomorrow = now_msk + timedelta(days=1)
        return tomorrow.replace(hour=AUTOPUBLISH_START_HOUR, minute=0, second=0, microsecond=0)
    
    # Если сейчас в разрешенном времени (8:00-22:00) - возвращаем текущее время
    return now_msk


def get_next_scheduled_time_for_publication(now_msk: datetime = None) -> datetime:
    """
    Получить время для публикации при попытке публикации
    Использует глобальную константу AUTOPUBLISH_START_HOUR из app.config
    Если сейчас в разрешенном времени - ставим на следующее свободное время начиная с начала следующего дня
    Если сейчас вне разрешенного времени - ставим на ближайшее разрешенное время
    """
    if now_msk is None:
        now_msk = get_moscow_time()
    
    # Всегда ставим на следующий день, ближайшее свободное время начиная с начала рабочего дня
    tomorrow = now_msk + timedelta(days=1)
    return tomorrow.replace(hour=AUTOPUBLISH_START_HOUR, minute=0, second=0, microsecond=0)


def msk_to_utc(msk_time: datetime) -> datetime:
    """
    Конвертировать время из системного часового пояса (МСК) в UTC для сохранения в БД
    Использует глобальную переменную SYSTEM_TIMEZONE из app.config
    """
    try:
        from zoneinfo import ZoneInfo
        SYSTEM_TZ = ZoneInfo(SYSTEM_TIMEZONE)
        UTC_TZ = ZoneInfo('UTC')
    except ImportError:
        import pytz
        SYSTEM_TZ = pytz.timezone(SYSTEM_TIMEZONE)
        UTC_TZ = pytz.timezone('UTC')
    
    # Создаем datetime с системной таймзоной
    system_time_with_tz = msk_time.replace(tzinfo=SYSTEM_TZ)
    # Конвертируем в UTC
    utc_time = system_time_with_tz.astimezone(UTC_TZ).replace(tzinfo=None)
    return utc_time


def utc_to_msk(utc_time: datetime) -> datetime:
    """
    Конвертировать UTC время в системный часовой пояс (МСК) для отображения
    Использует глобальную переменную SYSTEM_TIMEZONE из app.config
    """
    try:
        from zoneinfo import ZoneInfo
        SYSTEM_TZ = ZoneInfo(SYSTEM_TIMEZONE)
        UTC_TZ = ZoneInfo('UTC')
    except ImportError:
        import pytz
        SYSTEM_TZ = pytz.timezone(SYSTEM_TIMEZONE)
        UTC_TZ = pytz.timezone('UTC')
    
    # Создаем datetime с UTC таймзоной
    utc_time_with_tz = utc_time.replace(tzinfo=UTC_TZ)
    # Конвертируем в системный часовой пояс
    system_time = utc_time_with_tz.astimezone(SYSTEM_TZ).replace(tzinfo=None)
    return system_time


def is_within_publish_hours(now_msk: datetime = None) -> bool:
    """
    Проверить, находится ли текущее время в разрешенных часах для публикации (8:00-22:00 МСК)
    Использует глобальные константы AUTOPUBLISH_START_HOUR и AUTOPUBLISH_END_HOUR из app.config
    """
    if now_msk is None:
        now_msk = get_moscow_time()
    
    return AUTOPUBLISH_START_HOUR <= now_msk.hour < AUTOPUBLISH_END_HOUR

