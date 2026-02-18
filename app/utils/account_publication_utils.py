"""
Утилиты для работы с автопубликацией через аккаунты
Режимы: safe (10 мин), normal (5 мин), aggressive (2 мин), smart (равномерно 8:00-22:00)
"""
from datetime import datetime, timedelta
from app.config import AUTOPUBLISH_START_HOUR, AUTOPUBLISH_END_HOUR


def get_interval_minutes(mode: str) -> int:
    """
    Получить интервал между публикациями в минутах для режима
    safe: 10 минут
    normal: 5 минут
    aggressive: 2 минуты
    smart: не используется (равномерное распределение)
    """
    intervals = {
        'safe': 10,
        'normal': 5,
        'aggressive': 2,
        'smart': 0,  # Не используется для интервалов
    }
    return intervals.get(mode, 5)  # По умолчанию normal


def calculate_smart_schedule(total_tasks: int, daily_limit: int, start_time_msk: datetime) -> list[datetime]:
    """
    Равномерно распределить задачи в течение дня (8:00-22:00 МСК)
    Учитывает daily_limit аккаунта
    
    Args:
        total_tasks: Общее количество задач
        daily_limit: Дневной лимит аккаунта
        start_time_msk: Время начала (8:00 МСК)
    
    Returns:
        Список времени публикации (МСК)
    """
    # Ограничиваем количество задач лимитом
    tasks_count = min(total_tasks, daily_limit)
    
    if tasks_count == 0:
        return []
    
    # Время работы: 8:00-22:00 = 14 часов = 840 минут
    work_duration_minutes = (AUTOPUBLISH_END_HOUR - AUTOPUBLISH_START_HOUR) * 60
    
    # Равномерно распределяем задачи
    if tasks_count == 1:
        # Если одна задача - ставим на начало дня
        return [start_time_msk]
    
    # Интервал между задачами
    interval_minutes = work_duration_minutes / (tasks_count - 1)
    
    schedule = []
    current_time = start_time_msk
    
    for i in range(tasks_count):
        schedule.append(current_time)
        if i < tasks_count - 1:  # Не добавляем интервал после последней задачи
            current_time = current_time + timedelta(minutes=interval_minutes)
    
    return schedule


def calculate_scheduled_times_for_account(
    mode: str,
    total_tasks: int,
    daily_limit: int,
    start_time_msk: datetime
) -> list[datetime]:
    """
    Рассчитать время публикации для всех задач аккаунта
    
    Args:
        mode: Режим аккаунта (safe/normal/aggressive/smart)
        total_tasks: Общее количество задач
        daily_limit: Дневной лимит аккаунта
        start_time_msk: Время начала (8:00 МСК)
    
    Returns:
        Список времени публикации (МСК)
    """
    # Ограничиваем количество задач лимитом
    tasks_count = min(total_tasks, daily_limit)
    
    if tasks_count == 0:
        return []
    
    if mode == 'smart':
        # Равномерное распределение
        return calculate_smart_schedule(total_tasks, daily_limit, start_time_msk)
    
    # Для остальных режимов - последовательно с интервалами
    interval_minutes = get_interval_minutes(mode)
    schedule = []
    current_time = start_time_msk
    
    for i in range(tasks_count):
        schedule.append(current_time)
        if i < tasks_count - 1:  # Не добавляем интервал после последней задачи
            current_time = current_time + timedelta(minutes=interval_minutes)
            # Проверяем, не вышли ли за пределы рабочего времени
            if current_time.hour >= AUTOPUBLISH_END_HOUR:
                # Если вышли - останавливаемся
                break
    
    return schedule

