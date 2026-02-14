"""
Единая система логирования для бота - использует общие стандарты из app/utils/logger.py
Цель: тотальное логирование всех действий пользователя и событий системы
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from bot.database import get_db
from bot.models import ActionLog

# Используем ту же структуру папок, что и в app
LOG_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')


# Импортируем общие форматтеры из app (единый стандарт для всего проекта)
try:
    from app.utils.log_formatters import get_log_formatters
except ImportError:
    # Fallback если app недоступен (для автономного запуска бота)
    def get_log_formatters():
        """Fallback форматтеры если app недоступен"""
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-25s | %(funcName)-30s | %(lineno)-4d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        simple_formatter = logging.Formatter(
            '[%(asctime)s] | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        return detailed_formatter, simple_formatter


def setup_bot_logging():
    """
    Настройка логирования для бота с использованием единых стандартов
    Логирует: все действия пользователя, события системы, ошибки
    """
    # Создаём папку для логов
    os.makedirs(LOG_FOLDER, exist_ok=True)
    
    # Получаем форматтеры
    detailed_formatter, simple_formatter = get_log_formatters()
    
    # Логгер для бота
    logger = logging.getLogger('bot')
    logger.setLevel(logging.DEBUG)
    
    # Очищаем существующие обработчики
    if logger.handlers:
        logger.handlers.clear()
    
    # Настройка stdout для Docker (небуферизованный вывод)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(line_buffering=True)
    
    # Консольный обработчик (INFO и выше)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    console_handler.stream = sys.stdout
    
    # ========== PRODUCTION LOGS (постоянные, ротируемые) ==========
    
    # Файл всех логов (ротация: 10MB, 10 файлов)
    all_logs_file = os.path.join(LOG_FOLDER, 'bot.log')
    file_handler = logging.handlers.RotatingFileHandler(
        all_logs_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8',
        delay=False
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    file_handler.terminator = '\n'  # Принудительный flush
    
    # Файл только ошибок (ротация: 5MB, 5 файлов)
    error_logs_file = os.path.join(LOG_FOLDER, 'bot_errors.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_logs_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # ========== TEST LOGS (очищаются при деплое, для анализа нейросетью) ==========
    
    # Тестовые логи бота (очищаются при каждом деплое)
    test_bot_logs_file = os.path.join(LOG_FOLDER, 'test_bot.log')
    test_bot_handler = logging.FileHandler(
        test_bot_logs_file,
        mode='a',  # Append mode (очищается deploy.sh)
        encoding='utf-8'
    )
    test_bot_handler.setLevel(logging.DEBUG)
    test_bot_handler.setFormatter(detailed_formatter)
    
    # Тестовые ошибки бота
    test_bot_errors_file = os.path.join(LOG_FOLDER, 'test_bot_errors.log')
    test_bot_errors_handler = logging.FileHandler(
        test_bot_errors_file,
        mode='a',  # Append mode (очищается deploy.sh)
        encoding='utf-8'
    )
    test_bot_errors_handler.setLevel(logging.ERROR)
    test_bot_errors_handler.setFormatter(detailed_formatter)
    
    # Добавляем обработчики
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(test_bot_handler)
    logger.addHandler(test_bot_errors_handler)
    
    # Настройка уровней для библиотек
    logging.getLogger('telegram').setLevel(logging.INFO)  # INFO для деталей бота
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    
    # Логгер для обработчиков бота (наследует от bot)
    handlers_logger = logging.getLogger('bot.handlers')
    handlers_logger.setLevel(logging.DEBUG)
    handlers_logger.propagate = True  # Пропагирует к родительскому 'bot' логгеру
    
    return logger


def log_bot_action(action: str, user_id: int = None, telegram_id: str = None, 
                   details: dict = None, username: str = None):
    """
    Логирование действия пользователя бота в БД и файл
    Цель: тотальное логирование всех действий для анализа
    
    Args:
        action: Название действия (например, 'bot_command_start', 'object_created')
        user_id: ID пользователя в БД (опционально)
        telegram_id: Telegram ID пользователя (опционально)
        details: Дополнительные детали как словарь
        username: Username пользователя (опционально)
    """
    logger = logging.getLogger('bot.actions')
    
    db = None
    try:
        db = get_db()
        
        # Если user_id не передан, пытаемся найти пользователя по telegram_id
        if user_id is None and telegram_id:
            from bot.models import User
            user = db.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                user_id = user.user_id
        
        # Создаём запись в БД
        log_entry = ActionLog(
            user_id=user_id,
            action=action,
            details_json=details or {},
            created_at=datetime.utcnow()
        )
        # get_db() возвращает SQLAlchemy Session, поэтому используем методы сессии напрямую
        db.add(log_entry)
        db.commit()
        
        # Логируем в файл
        user_info = f"UserID: {user_id}" if user_id else f"TelegramID: {telegram_id}"
        username_info = f" (@{username})" if username else ""
        details_str = f" | Details: {details}" if details else ""
        logger.info(f"Action: {action} | {user_info}{username_info}{details_str}")
        
    except Exception as e:
        # Не падаем, если логирование не удалось
        logger.error(f"Failed to log bot action {action}: {e}", exc_info=True)
        try:
            if db is None:
                db = get_db()
            db.rollback()
        except Exception:
            pass
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass


def log_bot_error(error: Exception, action: str = None, user_id: int = None, 
                  telegram_id: str = None, details: dict = None):
    """
    Логирование ошибки бота в БД и файл
    Цель: полная трассировка всех ошибок для диагностики
    
    Args:
        error: Объект исключения
        action: Действие, которое вызвало ошибку
        user_id: ID пользователя в БД
        telegram_id: Telegram ID пользователя
        details: Дополнительные детали
    """
    logger = logging.getLogger('bot.errors')
    
    try:
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'action': action,
        }
        if details:
            error_details.update(details)
        
        # Логируем в файл с полным traceback
        logger.error(
            f"Error in {action or 'unknown'}: {type(error).__name__}: {str(error)}",
            exc_info=True
        )
        
        # Логируем в БД
        log_bot_action(
            action=action or 'bot_error_occurred',
            user_id=user_id,
            telegram_id=telegram_id,
            details=error_details
        )
    except Exception:
        # Не падаем, если логирование ошибки не удалось
        pass

