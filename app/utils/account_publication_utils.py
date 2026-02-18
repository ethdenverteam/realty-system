"""
Утилиты для работы с автопубликацией через аккаунты
Режимы интервалов:
- safe: 10 минут + джиттер
- normal: 5 минут + джиттер
- aggressive: 2 минуты + джиттер
- smart: равномерно на весь день (8:00-22:00 МСК, 14 часов)
- fix: фиксированный интервал (n минут, задается в TelegramAccount.fix_interval_minutes)
"""
from datetime import datetime, timedelta
import random
from app.config import AUTOPUBLISH_START_HOUR, AUTOPUBLISH_END_HOUR


def get_interval_minutes(mode: str, fix_interval: int = None) -> int:
    """
    Получить интервал между публикациями в минутах для режима
    safe: 10 минут
    normal: 5 минут
    aggressive: 2 минуты
    smart: не используется (равномерное распределение)
    fix: фиксированный интервал (из параметра fix_interval)
    """
    intervals = {
        'safe': 10,
        'normal': 5,
        'aggressive': 2,
        'smart': 0,  # Не используется для интервалов
        'fix': fix_interval if fix_interval is not None else 5,  # По умолчанию 5, если не указан
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
    start_time_msk: datetime,
    fix_interval: int = None
) -> list[datetime]:
    """
    Рассчитать время публикации для всех задач аккаунта
    Логика распределения: сначала все чаты первого объекта, потом второго и т.д.
    
    Args:
        mode: Режим аккаунта (safe/normal/aggressive/smart/fix)
        total_tasks: Общее количество задач
        daily_limit: Дневной лимит аккаунта
        start_time_msk: Время начала (8:00 МСК)
        fix_interval: Фиксированный интервал в минутах для режима 'fix'
    
    Returns:
        Список времени публикации (МСК) с джиттером для режимов safe/normal/aggressive/fix
    """
    # Ограничиваем количество задач лимитом
    tasks_count = min(total_tasks, daily_limit)
    
    if tasks_count == 0:
        return []
    
    if mode == 'smart':
        # Равномерное распределение на весь день
        return calculate_smart_schedule(total_tasks, daily_limit, start_time_msk)
    
    # Для остальных режимов - последовательно с интервалами + джиттер
    interval_minutes = get_interval_minutes(mode, fix_interval)
    schedule = []
    current_time = start_time_msk
    
    for i in range(tasks_count):
        schedule.append(current_time)
        if i < tasks_count - 1:  # Не добавляем интервал после последней задачи
            # Добавляем джиттер: случайное число секунд от 1 до 99
            jitter_seconds = random.randint(1, 99)
            current_time = current_time + timedelta(minutes=interval_minutes, seconds=jitter_seconds)
            
            # Проверяем, не вышли ли за пределы рабочего времени
            if current_time.hour >= AUTOPUBLISH_END_HOUR:
                # Если вышли - останавливаемся
                break
    
    return schedule

