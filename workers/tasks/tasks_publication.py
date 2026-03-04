"""
Celery tasks for publication
Логика: публикация объектов в Telegram через бота
"""
from workers.celery_app import celery_app
from app.database import db
from bot.models import PublicationQueue, Object, Chat, PublicationHistory, AutopublishConfig, TelegramAccount
from datetime import datetime, timedelta
from sqlalchemy import or_, func
import logging
import asyncio
import random

from bot.utils import get_districts_config
from app.utils.time_utils import (
    get_moscow_time,
    get_next_allowed_time_msk,
    get_next_scheduled_time_for_publication,
    is_within_publish_hours,
    msk_to_utc
)
from app.utils.telethon_client import subscribe_to_chat, run_async
from app.database import db as app_db
from app.models.chat_subscription_task import ChatSubscriptionTask
from app.models.chat import Chat as AppChat
from app.models.chat_group import ChatGroup as AppChatGroup
from app.models.telegram_account_chat import TelegramAccountChat as AppTelegramAccountChat
from app.models.telegram_account import TelegramAccount as AppTelegramAccount
from app.utils.account_publication_utils import calculate_scheduled_times_for_account

logger = logging.getLogger(__name__)

@celery_app.task(name='workers.tasks.publish_to_telegram')
def publish_to_telegram(queue_id: int):
    """
    Публикация объекта недвижимости в Telegram чат
    Логика: проверка дубликатов (24 часа), форматирование текста, отправка через API, создание истории
    Все этапы логируются для отслеживания процесса публикации
    """
    from app import app
    from celery.exceptions import SoftTimeLimitExceeded
    
    with app.app_context():
        queue = db.session.query(PublicationQueue).get(queue_id)
        if not queue:
            logger.error(f"Queue {queue_id} not found")
            return False
        
        # Update status
        queue.status = 'processing'
        queue.started_at = datetime.utcnow()
        db.session.commit()
        
        # Get object and chat
        obj = db.session.query(Object).get(queue.object_id)
        chat = db.session.query(Chat).get(queue.chat_id)
        
        if not obj or not chat:
            queue.status = 'failed'
            queue.error_message = 'Object or chat not found'
            db.session.commit()
            return False
        
        # Проверка времени для автопубликации: публикация разрешена только с 8:00 до 22:00 МСК
        # Исключение: если админ включил обход ограничения времени
        if queue.mode == 'autopublish':
            # ВАЖНО: Проверяем, что автопубликация все еще включена для объекта
            from app.models.autopublish_config import AutopublishConfig as AppAutopublishConfig
            autopublish_cfg = AppAutopublishConfig.query.filter_by(object_id=queue.object_id).first()
            
            if not autopublish_cfg or not autopublish_cfg.enabled:
                logger.warning(f"Autopublish disabled for object {queue.object_id}, cancelling queue {queue_id}")
                queue.status = 'failed'
                queue.error_message = 'Autopublish disabled for this object'
                db.session.commit()
                return False
            
            # Для бота проверяем bot_enabled
            if queue.type == 'bot' and not autopublish_cfg.bot_enabled:
                logger.warning(f"Bot autopublish disabled for object {queue.object_id}, cancelling queue {queue_id}")
                queue.status = 'failed'
                queue.error_message = 'Bot autopublish disabled for this object'
                db.session.commit()
                return False
            
            # Проверяем настройку обхода ограничения времени для админа (через app контекст)
            admin_bypass_enabled = False
            is_admin = False
            
            from app.models.system_setting import SystemSetting
            time_limit_setting = SystemSetting.query.filter_by(key='admin_bypass_time_limit').first()
            if time_limit_setting and isinstance(time_limit_setting.value_json, dict):
                admin_bypass_enabled = time_limit_setting.value_json.get('enabled', False)
            
            # Проверяем, является ли пользователь админом
            if queue.user_id:
                from app.models.user import User
                user = User.query.get(queue.user_id)
                if user and user.web_role == 'admin':
                    is_admin = True
            
            # Если админ и включен обход - пропускаем проверку времени
            if not (is_admin and admin_bypass_enabled):
                now_msk = get_moscow_time()
                if not is_within_publish_hours(now_msk):
                    logger.info(f"Outside publish hours (8:00-22:00 МСК), rescheduling queue {queue_id}")
                    # Переносим на ближайшее разрешенное время
                    next_time_msk = get_next_allowed_time_msk(now_msk)
                    next_time_utc = msk_to_utc(next_time_msk)
                    queue.scheduled_time = next_time_utc
                    queue.status = 'pending'
                    db.session.commit()
                    return False
        
        # Проверка дубликатов через унифицированную утилиту
        from app.utils.duplicate_checker import check_duplicate_publication
        
        # Определяем тип публикации
        publication_type = 'autopublish_bot' if queue.mode == 'autopublish' else 'manual_bot'
        
        can_publish, reason = check_duplicate_publication(
            object_id=queue.object_id,
            chat_id=queue.chat_id,
            account_id=None,  # Бот
            publication_type=publication_type,
            user_id=queue.user_id,
            allow_duplicates_setting=None  # Получит из SystemSetting автоматически
        )
        
        if not can_publish:
            logger.info(f"Object {queue.object_id} cannot be published to chat {queue.chat_id} via bot: {reason}")
            queue.status = 'failed'
            queue.error_message = reason
            db.session.commit()
            return False
        
        # Реализация публикации через Telegram API
        import requests
        import os
        from bot.config import BOT_TOKEN
        from bot.utils import format_publication_text
        from bot.models import User as BotUser
        
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN is not configured")
            queue.status = 'failed'
            queue.error_message = 'BOT_TOKEN is not configured'
            db.session.commit()
            return False
        
        # Получаем пользователя бота для форматирования текста
        bot_user = None
        if obj.user_id:
            bot_user = db.session.query(BotUser).filter_by(user_id=obj.user_id).first()
        
        # Получаем формат публикации из конфигурации автопубликации
        publication_format = 'default'
        try:
            from app.database import db as web_db
            from app.models.autopublish_config import AutopublishConfig as WebAutopublishConfig
            web_cfg = web_db.session.query(WebAutopublishConfig).filter_by(
                object_id=obj.object_id
            ).first()
            if web_cfg and web_cfg.accounts_config_json:
                accounts_cfg = web_cfg.accounts_config_json
                if isinstance(accounts_cfg, dict):
                    publication_format = accounts_cfg.get('publication_format', 'default')
        except Exception:
            # Если не удалось получить конфигурацию, используем формат по умолчанию
            pass
        
        # Форматируем текст публикации
        publication_text = format_publication_text(obj, bot_user, is_preview=False, publication_format=publication_format)
        
        # Отправляем сообщение - всегда отправляем фото если оно есть
        photos_json = obj.photos_json or []
        
        try:
            if photos_json and len(photos_json) > 0:
                # Берем первое фото (только одно фото разрешено)
                photo_data = photos_json[0]
                
                # Извлекаем путь к файлу - всегда используем путь к файлу на сервере
                photo_path = None
                if isinstance(photo_data, dict):
                    # Если это объект - берем path
                    photo_path = photo_data.get('path', '')
                elif isinstance(photo_data, str):
                    # Если это строка - это путь к файлу
                    photo_path = photo_data
                
                # Загружаем файл с сервера и отправляем
                if photo_path:
                    import os
                    from app.config import Config
                    
                    # Используем Config.UPLOAD_FOLDER напрямую
                    # photo_path может быть "uploads/filename.jpg" или просто "filename.jpg"
                    if photo_path.startswith('uploads/'):
                        # Убираем префикс "uploads/" и используем Config.UPLOAD_FOLDER
                        filename = photo_path.replace('uploads/', '', 1)
                        full_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                    elif photo_path.startswith('/'):
                        # Абсолютный путь
                        full_path = photo_path
                    else:
                        # Относительный путь - используем Config.UPLOAD_FOLDER
                        full_path = os.path.join(Config.UPLOAD_FOLDER, photo_path)
                    
                    if os.path.exists(full_path):
                        url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto'
                        with open(full_path, 'rb') as photo_file:
                            files = {'photo': photo_file}
                            payload = {
                                'chat_id': chat.telegram_chat_id,
                                'caption': publication_text,
                                'parse_mode': 'HTML'
                            }
                            response = requests.post(url, files=files, data=payload, timeout=30)
                    else:
                        logger.warning(f"Photo file not found: {full_path}, sending text only")
                        url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
                        payload = {
                            'chat_id': chat.telegram_chat_id,
                            'text': publication_text,
                            'parse_mode': 'HTML'
                        }
                        response = requests.post(url, json=payload, timeout=10)
                else:
                    # Если путь не найден - отправляем только текст
                    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
                    payload = {
                        'chat_id': chat.telegram_chat_id,
                        'text': publication_text,
                        'parse_mode': 'HTML'
                    }
                    response = requests.post(url, json=payload, timeout=10)
            else:
                # Если фото нет - отправляем только текст
                url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
                payload = {
                    'chat_id': chat.telegram_chat_id,
                    'text': publication_text,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, json=payload, timeout=10)
            
            response.raise_for_status()
            result = response.json()
            
            if not result.get('ok'):
                error_description = result.get('description', 'Unknown error')
                logger.error(f"Failed to publish: {error_description}")
                queue.status = 'failed'
                queue.error_message = error_description
                db.session.commit()
                return False
            
            message_id = result.get('result', {}).get('message_id')
            
            # Успешная публикация
            queue.status = 'completed'
            queue.completed_at = datetime.utcnow()
            queue.message_id = str(message_id) if message_id else None
            
            # Создаем запись в истории
            history = PublicationHistory(
                queue_id=queue_id,
                object_id=obj.object_id,
                chat_id=chat.chat_id,
                account_id=queue.account_id,
                published_at=datetime.utcnow(),
                message_id=queue.message_id
            )
            db.session.add(history)
            
            # Обновляем статистику чата
            chat.total_publications = (chat.total_publications or 0) + 1
            chat.last_publication = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Successfully published object {obj.object_id} to chat {chat.telegram_chat_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending message to Telegram: {e}")
            if queue:
                queue.status = 'failed'
                queue.error_message = str(e)
                db.session.commit()
            return False
        
        except SoftTimeLimitExceeded:
            logger.warning(f"SoftTimeLimitExceeded in publish_to_telegram for queue {queue_id}")
            if queue:
                queue.status = 'failed'
                queue.error_message = 'Task timeout - exceeded soft time limit'
                queue.attempts += 1
                db.session.commit()
            return False
        
        except Exception as e:
            logger.error(f"Error publishing to Telegram: {e}", exc_info=True)
            if queue:
                queue.status = 'failed'
                queue.error_message = str(e)
                queue.attempts += 1
                db.session.commit()
            return False


