"""
Общие форматтеры логов для всего проекта
Цель: единый формат логов для анализа нейросетью, переиспользование в app и bot
"""
import logging


def get_log_formatters():
    """
    Возвращает стандартные форматтеры логов (единые для всего проекта)
    Цель: единый формат логов для анализа нейросетью
    
    Returns:
        tuple: (detailed_formatter, simple_formatter)
    """
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-25s | %(funcName)-30s | %(lineno)-4d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    return detailed_formatter, simple_formatter

