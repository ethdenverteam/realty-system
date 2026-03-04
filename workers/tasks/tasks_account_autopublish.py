"""
Celery tasks for account autopublish
Логика: автопубликация от имени аккаунтов пользователей
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

@celery_app.task(name='workers.tasks.process_account_autopublish')
def process_account_autopublish():
    """
    Обработка очередей публикаций для аккаунтов пользователей
    Обрабатывает все аккаунты параллельно, учитывая лимиты каждого
    """
    from app import app
    from app.models.account_publication_queue import AccountPublicationQueue
    from app.models.object import Object as AppObject
    from app.models.chat import Chat as AppChat
    from app.models.telegram_account import TelegramAccount as AppTelegramAccount
    from app.models.publication_history import PublicationHistory as AppPublicationHistory
    from app.models.system_setting import SystemSetting
    from app.utils.telethon_client import send_object_message, run_async
    from app.utils.rate_limiter import get_rate_limit_status
    from bot.utils import format_publication_text
    from bot.models import User as BotUser, Object as BotObject
    from celery.exceptions import SoftTimeLimitExceeded
    
    processed_count = 0
    
    logger.info("🚀 process_account_autopublish: Starting task")
    
    try:
        with app.app_context():
            try:
                now = datetime.utcnow()
                logger.info(f"process_account_autopublish: Current time UTC: {now}")
                
                # Получаем настройку проверки дубликатов
                # Используем SystemSetting.query напрямую, так как мы уже в app_context
                duplicates_setting = SystemSetting.query.filter_by(key='allow_duplicates').first()
                allow_duplicates = False
                if duplicates_setting and isinstance(duplicates_setting.value_json, dict):
                    allow_duplicates = duplicates_setting.value_json.get('enabled', False)
                
                logger.info(f"process_account_autopublish: Duplicates allowed: {allow_duplicates}")
                
                # Получаем все активные аккаунты
                accounts = app_db.session.query(AppTelegramAccount).filter_by(is_active=True).all()
                logger.info(f"process_account_autopublish: Found {len(accounts)} active accounts")
                
                # Проверяем количество pending задач
                total_pending = app_db.session.query(AccountPublicationQueue).filter(
                    AccountPublicationQueue.status == 'pending',
                    AccountPublicationQueue.scheduled_time <= now
                ).count()
                logger.info(f"process_account_autopublish: Found {total_pending} pending tasks ready for processing")
                work_items = []
                
                for account in accounts:
                    # Проверяем лимит аккаунта (по успешным публикациям за сегодня)
                    try:
                        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                        # Используем scalar() для получения одного значения вместо count()
                        today_publications = app_db.session.query(
                            func.count(AppPublicationHistory.history_id)
                        ).filter(
                            AppPublicationHistory.account_id == account.account_id,
                            AppPublicationHistory.published_at >= today_start,
                            AppPublicationHistory.deleted == False
                        ).scalar() or 0
                    except Exception as e:
                        logger.error(f"Error checking daily limit for account {account.account_id}: {e}", exc_info=True)
                        continue
                    
                    if today_publications >= account.daily_limit:
                        # Лимит достигнут - пропускаем этот аккаунт
                        logger.info(f"Account {account.account_id} ({account.phone}) reached daily limit ({today_publications}/{account.daily_limit})")
                        continue
                    
                    # Получаем задачи аккаунта, готовые к публикации
                    queues = app_db.session.query(AccountPublicationQueue).filter(
                        AccountPublicationQueue.account_id == account.account_id,
                        AccountPublicationQueue.status == 'pending',
                        AccountPublicationQueue.scheduled_time <= now
                    ).order_by(
                        AccountPublicationQueue.scheduled_time.asc()
                    ).limit(10).all()  # Обрабатываем по 10 задач за раз
                    
                    if not queues:
                        continue
                    
                    logger.info(f"Processing {len(queues)} tasks for account {account.account_id} ({account.phone})")
                    for queue in queues:
                        work_items.append((account, queue))
                
                for account, queue in work_items:
                    try:
                        logger.info(f"Starting publication for queue {queue.queue_id}: object {queue.object_id} to chat {queue.chat_id} via account {account.account_id}")
                        # Обновляем статус
                        queue.status = 'processing'
                        queue.started_at = datetime.utcnow()
                        queue.attempts += 1
                        app_db.session.commit()
                        
                        # Получаем объект и чат
                        obj = app_db.session.query(AppObject).get(queue.object_id)
                        chat = app_db.session.query(AppChat).get(queue.chat_id)
                        
                        if not obj or not chat:
                            queue.status = 'failed'
                            queue.error_message = 'Object or chat not found'
                            app_db.session.commit()
                            continue
                        
                        # ВАЖНО: Проверяем, что автопубликация все еще включена для объекта
                        from app.models.autopublish_config import AutopublishConfig
                        autopublish_cfg = app_db.session.query(AutopublishConfig).filter_by(
                            object_id=queue.object_id
                        ).first()
                        
                        if not autopublish_cfg or not autopublish_cfg.enabled:
                            logger.warning(f"Autopublish disabled for object {queue.object_id}, cancelling account queue {queue.queue_id}")
                            queue.status = 'failed'
                            queue.error_message = 'Autopublish disabled for this object'
                            app_db.session.commit()
                            continue
                        
                        # Проверяем, что для этого аккаунта и чата автопубликация включена
                        if autopublish_cfg.accounts_config_json:
                            accounts_cfg = autopublish_cfg.accounts_config_json
                            if isinstance(accounts_cfg, dict):
                                accounts = accounts_cfg.get('accounts', [])
                                account_found = False
                                for acc_cfg in accounts:
                                    if acc_cfg.get('account_id') == queue.account_id:
                                        chat_ids = acc_cfg.get('chat_ids', [])
                                        if queue.chat_id in chat_ids:
                                            account_found = True
                                            break
                                
                                if not account_found:
                                    logger.warning(f"Account {queue.account_id} or chat {queue.chat_id} not in autopublish config for object {queue.object_id}, cancelling queue {queue.queue_id}")
                                    queue.status = 'failed'
                                    queue.error_message = 'Account or chat not in autopublish config'
                                    app_db.session.commit()
                                    continue
                        
                        # Проверка дубликатов через унифицированную утилиту
                        from app.utils.duplicate_checker import check_duplicate_publication
                        can_publish, reason = check_duplicate_publication(
                            object_id=queue.object_id,
                            chat_id=queue.chat_id,
                            account_id=queue.account_id,
                            publication_type='autopublish_account',
                            user_id=queue.user_id,
                            allow_duplicates_setting=None  # Получит из SystemSetting автоматически
                        )
                        
                        if not can_publish:
                            logger.info(f"Object {queue.object_id} cannot be published to chat {queue.chat_id} via account {queue.account_id}: {reason}")
                            queue.status = 'failed'
                            queue.error_message = reason
                            app_db.session.commit()
                            continue
                        
                        # Проверка rate limit
                        rate_status = get_rate_limit_status(account.phone)
                        if not rate_status['can_send']:
                            # Откладываем задачу на следующую минуту
                            queue.status = 'pending'
                            queue.scheduled_time = datetime.utcnow() + timedelta(minutes=1)
                            app_db.session.commit()
                            continue
                        
                        # Получаем bot объект для форматирования
                        bot_user = None
                        if obj.user_id:
                            bot_user = app_db.session.query(BotUser).filter_by(user_id=obj.user_id).first()
                        
                        bot_obj = app_db.session.query(BotObject).filter_by(object_id=obj.object_id).first()
                        if not bot_obj:
                            # Создаем bot object из web object
                            bot_obj = BotObject(
                                object_id=obj.object_id,
                                user_id=obj.user_id,
                                rooms_type=obj.rooms_type,
                                price=obj.price,
                                districts_json=obj.districts_json,
                                region=obj.region,
                                city=obj.city,
                                photos_json=obj.photos_json,
                                area=obj.area,
                                floor=obj.floor,
                                address=obj.address,
                                residential_complex=obj.residential_complex,
                                renovation=obj.renovation,
                                comment=obj.comment,
                                contact_name=obj.contact_name,
                                show_username=obj.show_username,
                                phone_number=obj.phone_number,
                                contact_name_2=obj.contact_name_2,
                                phone_number_2=obj.phone_number_2,
                                status=obj.status,
                                source='web'
                            )
                            app_db.session.add(bot_obj)
                            app_db.session.commit()
                        
                        # Получаем формат публикации
                        publication_format = 'default'
                        from app.models.autopublish_config import AutopublishConfig
                        autopublish_cfg = app_db.session.query(AutopublishConfig).filter_by(
                            object_id=obj.object_id
                        ).first()
                        if autopublish_cfg and autopublish_cfg.accounts_config_json:
                            accounts_cfg = autopublish_cfg.accounts_config_json
                            if isinstance(accounts_cfg, dict):
                                publication_format = accounts_cfg.get('publication_format', 'default')
                        
                        # Форматируем текст публикации
                        publication_text = format_publication_text(bot_obj, bot_user, is_preview=False, publication_format=publication_format)
                        
                        # Отправляем через Telethon
                        try:
                            success, error_msg, message_id = run_async(
                                send_object_message(
                                    account.phone,
                                    chat.telegram_chat_id,
                                    publication_text,
                                    obj.photos_json or []
                                )
                            )
                        except Exception as send_error:
                            # Проверяем, не FloodWait ли это
                            error_str = str(send_error)
                            if 'FLOOD_WAIT' in error_str or 'FloodWaitError' in error_str:
                                # Извлекаем секунды из ошибки
                                wait_seconds = 3600  # По умолчанию 1 час
                                try:
                                    if 'FLOOD_WAIT:' in error_str:
                                        wait_seconds = int(error_str.split('FLOOD_WAIT:')[1].split()[0])
                                    elif 'seconds' in error_str:
                                        import re
                                        match = re.search(r'(\d+)\s*seconds?', error_str)
                                        if match:
                                            wait_seconds = int(match.group(1))
                                except:
                                    pass
                                
                                # FloodWait - останавливаем аккаунт
                                logger.error(f"FloodWaitError for account {account.account_id} ({account.phone}): wait {wait_seconds} seconds")
                                account.is_active = False
                                account.last_error = f"FLOOD_WAIT: {wait_seconds} seconds. Account deactivated. Please reactivate manually."
                                queue.status = 'flood_wait'
                                queue.error_message = f"FLOOD_WAIT: {wait_seconds} seconds"
                                app_db.session.commit()
                                # Записываем ошибку
                                from app.utils.logger import log_error
                                log_error(
                                    error=send_error,
                                    action='account_publication_flood_wait',
                                    user_id=queue.user_id,
                                    details={
                                        'account_id': account.account_id,
                                        'object_id': queue.object_id,
                                        'chat_id': queue.chat_id,
                                        'wait_seconds': wait_seconds
                                    }
                                )
                                processed_count += 1
                                continue
                            logger.error(f"Exception in send_object_message for account {account.account_id}: {send_error}", exc_info=True)
                            # Иные ошибки - пробуем повторить еще 2 раза в конце очереди
                            if queue.attempts < 3:
                                queue.status = 'pending'
                                queue.scheduled_time = datetime.utcnow() + timedelta(minutes=5)  # Откладываем на 5 минут
                                queue.error_message = str(send_error)
                                app_db.session.commit()
                                # Записываем ошибку
                                from app.utils.logger import log_error
                                log_error(
                                    error=send_error,
                                    action='account_publication_error',
                                    user_id=queue.user_id,
                                    details={
                                        'account_id': account.account_id,
                                        'object_id': queue.object_id,
                                        'chat_id': queue.chat_id,
                                        'attempt': queue.attempts
                                    }
                                )
                            else:
                                queue.status = 'failed'
                                queue.error_message = str(send_error)
                                app_db.session.commit()
                            continue
                        
                        if not success:
                            # Проверяем, не FloodWait ли это в error_msg
                            if error_msg and ('FLOOD_WAIT' in error_msg or 'FloodWaitError' in error_msg):
                                # Извлекаем секунды из ошибки
                                wait_seconds = 3600  # По умолчанию 1 час
                                try:
                                    if 'FLOOD_WAIT:' in error_msg:
                                        wait_seconds = int(error_msg.split('FLOOD_WAIT:')[1].split()[0])
                                    elif 'seconds' in error_msg:
                                        import re
                                        match = re.search(r'(\d+)\s*seconds?', error_msg)
                                        if match:
                                            wait_seconds = int(match.group(1))
                                except:
                                    pass
                                
                                # FloodWait - останавливаем аккаунт
                                logger.error(f"FloodWaitError for account {account.account_id} ({account.phone}): wait {wait_seconds} seconds")
                                account.is_active = False
                                account.last_error = f"FLOOD_WAIT: {wait_seconds} seconds. Account deactivated. Please reactivate manually."
                                queue.status = 'flood_wait'
                                queue.error_message = f"FLOOD_WAIT: {wait_seconds} seconds"
                                app_db.session.commit()
                                # Записываем ошибку
                                from app.utils.logger import log_error
                                log_error(
                                    error=Exception(error_msg),
                                    action='account_publication_flood_wait',
                                    user_id=queue.user_id,
                                    details={
                                        'account_id': account.account_id,
                                        'object_id': queue.object_id,
                                        'chat_id': queue.chat_id,
                                        'wait_seconds': wait_seconds
                                    }
                                )
                                processed_count += 1
                                continue
                            
                            # Иные ошибки - пробуем повторить
                            if queue.attempts < 3:
                                queue.status = 'pending'
                                queue.scheduled_time = datetime.utcnow() + timedelta(minutes=5)
                                queue.error_message = error_msg
                                app_db.session.commit()
                                # Записываем ошибку
                                from app.utils.logger import log_error
                                log_error(
                                    error=Exception(error_msg),
                                    action='account_publication_error',
                                    user_id=queue.user_id,
                                    details={
                                        'account_id': account.account_id,
                                        'object_id': queue.object_id,
                                        'chat_id': queue.chat_id,
                                        'attempt': queue.attempts,
                                        'error_message': error_msg
                                    }
                                )
                            else:
                                queue.status = 'failed'
                                queue.error_message = error_msg
                                app_db.session.commit()
                            continue
                        
                        # Успешная публикация
                        queue.status = 'completed'
                        queue.completed_at = datetime.utcnow()
                        queue.message_id = str(message_id) if message_id else None
                        
                        # Создаем запись в истории
                        history = AppPublicationHistory(
                            queue_id=None,  # Для account_publication_queues нет queue_id в PublicationHistory
                            object_id=obj.object_id,
                            chat_id=chat.chat_id,
                            account_id=account.account_id,
                            published_at=datetime.utcnow(),
                            message_id=queue.message_id,
                            deleted=False
                        )
                        app_db.session.add(history)
                        
                        # Обновляем статистику чата
                        chat.total_publications = (chat.total_publications or 0) + 1
                        chat.last_publication = datetime.utcnow()
                        
                        # Обновляем аккаунт
                        account.last_used = datetime.utcnow()
                        account.last_error = None
                        
                        app_db.session.commit()
                        processed_count += 1
                        logger.info(f"✅ Successfully published object {obj.object_id} via account {account.account_id} ({account.phone}) to chat {chat.telegram_chat_id} (message_id: {message_id})")
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing queue {queue.queue_id} for account {account.account_id} ({account.phone}): {e}", exc_info=True)
                        try:
                            queue.status = 'failed'
                            queue.error_message = str(e)
                            queue.attempts += 1
                            app_db.session.commit()
                        except Exception as commit_error:
                            logger.error(f"Failed to commit error status for queue {queue.queue_id}: {commit_error}", exc_info=True)
                            app_db.session.rollback()
                        # Записываем ошибку
                        from app.utils.logger import log_error
                        log_error(
                            error=e,
                            action='account_publication_error',
                            user_id=queue.user_id if queue else None,
                            details={
                                'account_id': account.account_id,
                                'queue_id': queue.queue_id if queue else None
                            }
                        )
            
                logger.info(f"process_account_autopublish: processed {processed_count} tasks")
                return processed_count
                
            except SoftTimeLimitExceeded as e:
                # Время выполнения задачи превысило soft time limit (240 секунд)
                # Помечаем все задачи в статусе 'processing' обратно в 'pending' для повторной обработки
                logger.warning(f"⚠️ SoftTimeLimitExceeded in process_account_autopublish (processed {processed_count} tasks so far) - resetting stuck tasks")
                try:
                    stuck_threshold = datetime.utcnow() - timedelta(minutes=5)
                    stuck_queues = app_db.session.query(AccountPublicationQueue).filter(
                        AccountPublicationQueue.status == 'processing',
                        AccountPublicationQueue.started_at < stuck_threshold
                    ).all()
                    
                    logger.warning(f"Found {len(stuck_queues)} stuck queues (processing for more than 5 minutes)")
                    
                    for stuck_queue in stuck_queues:
                        logger.warning(f"Resetting stuck queue {stuck_queue.queue_id} (started at {stuck_queue.started_at}, attempts: {stuck_queue.attempts})")
                        stuck_queue.status = 'pending'
                        stuck_queue.attempts += 1
                        if stuck_queue.attempts >= 3:
                            stuck_queue.status = 'failed'
                            stuck_queue.error_message = 'Task timeout - exceeded soft time limit'
                        app_db.session.commit()
                    
                    logger.info(f"Reset {len(stuck_queues)} stuck account publication tasks")
                except Exception as reset_error:
                    logger.error(f"Error resetting stuck tasks: {reset_error}", exc_info=True)
                    app_db.session.rollback()
                
                return processed_count
                
            except Exception as e:
                logger.error(f"❌ Error in process_account_autopublish: {e}", exc_info=True)
                app_db.session.rollback()
                return processed_count
                
    except SoftTimeLimitExceeded as e:
        # Обработка SoftTimeLimitExceeded на верхнем уровне (если произошло до входа в app_context)
        logger.error(f"⚠️ SoftTimeLimitExceeded in process_account_autopublish BEFORE app_context: {e}")
        # Пытаемся войти в контекст для сброса stuck задач
        try:
            with app.app_context():
                stuck_threshold = datetime.utcnow() - timedelta(minutes=5)
                stuck_queues = app_db.session.query(AccountPublicationQueue).filter(
                    AccountPublicationQueue.status == 'processing',
                    AccountPublicationQueue.started_at < stuck_threshold
                ).all()
                
                for stuck_queue in stuck_queues:
                    logger.warning(f"Resetting stuck queue {stuck_queue.queue_id} (started at {stuck_queue.started_at})")
                    stuck_queue.status = 'pending'
                    stuck_queue.attempts += 1
                    if stuck_queue.attempts >= 3:
                        stuck_queue.status = 'failed'
                        stuck_queue.error_message = 'Task timeout - exceeded soft time limit'
                    app_db.session.commit()
                
                logger.info(f"Reset {len(stuck_queues)} stuck account publication tasks")
        except Exception as reset_error:
            logger.error(f"Error resetting stuck tasks in outer handler: {reset_error}", exc_info=True)
        
        return processed_count
        
    except Exception as e:
        logger.error(f"❌ Critical error in process_account_autopublish (outside app_context): {e}", exc_info=True)
        return processed_count

