"""
Celery tasks for autopublish
Логика: автопубликация через бота, создание задач на день
"""
from workers.celery_app import celery_app
from app.database import db
from bot.models import PublicationQueue, Object, Chat, PublicationHistory, AutopublishConfig, TelegramAccount
from workers.tasks.tasks_publication import publish_to_telegram  # Celery-задача отправки в Telegram
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

@celery_app.task(name='workers.tasks.process_autopublish')
def process_autopublish():
    """Process autopublish queue - обрабатывает задачи в порядке scheduled_time"""
    from app import app
    from celery.exceptions import SoftTimeLimitExceeded
    
    try:
        with app.app_context():
            # Сбрасываем зависшие задачи в статусе 'processing'
            try:
                stuck_threshold = datetime.utcnow() - timedelta(minutes=5)
                stuck_queues = db.session.query(PublicationQueue).filter(
                    PublicationQueue.status == 'processing',
                    PublicationQueue.started_at < stuck_threshold
                ).all()
                
                for stuck_queue in stuck_queues:
                    logger.warning(f"Resetting stuck bot queue {stuck_queue.queue_id} (started at {stuck_queue.started_at})")
                    stuck_queue.status = 'pending'
                    stuck_queue.attempts += 1
                    if stuck_queue.attempts >= 3:
                        stuck_queue.status = 'failed'
                        stuck_queue.error_message = 'Task timeout - exceeded time limit'
                    db.session.commit()
                
                if stuck_queues:
                    logger.info(f"Reset {len(stuck_queues)} stuck bot publication tasks")
            except Exception as reset_error:
                logger.error(f"Error resetting stuck bot tasks: {reset_error}", exc_info=True)
            
            now = datetime.utcnow()
            
            # Get pending autopublish tasks that are ready to publish
            # Сортируем по scheduled_time (старейшие первыми), если scheduled_time не установлено - по created_at
            queues = db.session.query(PublicationQueue).filter(
                PublicationQueue.mode == 'autopublish',
                PublicationQueue.status == 'pending',
                or_(
                    PublicationQueue.scheduled_time <= now,
                    PublicationQueue.scheduled_time.is_(None)
                )
            ).order_by(
                PublicationQueue.scheduled_time.asc().nullslast(),
                PublicationQueue.created_at.asc()
            ).limit(10).all()  # Обрабатываем по 10 задач за раз
            
            logger.info(f"Processing {len(queues)} autopublish tasks")
            
            for queue in queues:
                scheduled_str = queue.scheduled_time.strftime('%Y-%m-%d %H:%M:%S') if queue.scheduled_time else 'not scheduled'
                logger.info(
                    f"Publishing queue {queue.queue_id} for object {queue.object_id} "
                    f"to chat {queue.chat_id} (scheduled: {scheduled_str}, created: {queue.created_at})"
                )
                try:
                    # Ставим задачу publish_to_telegram в очередь Celery
                publish_to_telegram.delay(queue.queue_id)
                except Exception as enqueue_error:
                    # ВАЖНО: если даже постановка задачи упала, помечаем очередь с ошибкой,
                    # чтобы она не висела в pending бесконечно.
                    logger.error(
                        f"Failed to enqueue publish_to_telegram for queue {queue.queue_id}: {enqueue_error}",
                        exc_info=True,
                    )
                    queue.status = 'failed'
                    queue.error_message = str(enqueue_error)
                    queue.attempts = (queue.attempts or 0) + 1
                    db.session.commit()
            
            return len(queues)
    except SoftTimeLimitExceeded:
        logger.warning("SoftTimeLimitExceeded in process_autopublish")
        return 0
    except Exception as e:
        logger.error(f"Error processing autopublish queue: {e}", exc_info=True)
        return 0


def _get_matching_bot_chats_for_object(db_session, obj: Object):
    """
    Подбор чатов бота для объекта по тем же правилам,
    что и ручная публикация через бота.
    """
    target_chats = []

    chats = db_session.query(Chat).filter_by(owner_type='bot', is_active=True).all()

    rooms_type = obj.rooms_type or ""
    districts = obj.districts_json or []
    price = obj.price or 0

    districts_config = get_districts_config()

    # Добавляем родительские районы
    all_districts = set(districts)
    for district in districts:
        if isinstance(district, str) and district in districts_config:
            parent_districts = districts_config[district]
            if isinstance(parent_districts, list):
                all_districts.update(parent_districts)

    for chat in chats:
        matches = False
        filters = chat.filters_json or {}
        
        # Проверка типа привязки "общий" - такой чат получает все посты
        binding_type = filters.get('binding_type')
        if binding_type == 'common':
            target_chats.append(chat)
            continue  # Пропускаем проверку фильтров для "общего" чата

        has_filters_json = bool(
            filters.get('rooms_types')
            or filters.get('districts')
            or filters.get('price_min') is not None
            or filters.get('price_max') is not None
        )

        if has_filters_json:
            rooms_match = True
            districts_match = True
            price_match = True

            if filters.get('rooms_types'):
                rooms_match = rooms_type in filters['rooms_types']

            if filters.get('districts'):
                chat_districts = set(filters['districts'])
                districts_match = bool(chat_districts.intersection(all_districts))

            price_min = filters.get('price_min')
            price_max = filters.get('price_max')
            if price_min is not None or price_max is not None:
                price_min = price_min or 0
                price_max = price_max if price_max is not None else float('inf')
                price_match = price_min <= price < price_max

            if rooms_match and districts_match and price_match:
                matches = True
        else:
            # Legacy category support
            category = chat.category or ""

            if category.startswith("rooms_") and category.replace("rooms_", "") == rooms_type:
                matches = True

            if category.startswith("district_"):
                district_name = category.replace("district_", "")
                if district_name in all_districts:
                    matches = True

            if category.startswith("price_"):
                try:
                    parts = category.replace("price_", "").split("_")
                    if len(parts) == 2:
                        min_price = float(parts[0])
                        max_price = float(parts[1])
                        if min_price <= price < max_price:
                            matches = True
                except Exception:
                    pass

        if matches:
            target_chats.append(chat)

    return target_chats


@celery_app.task(name='workers.tasks.schedule_daily_autopublish')
def schedule_daily_autopublish():
    """
    Создать задачи автопубликации для всех объектов с включенной автопубликацией.
    Предполагается запуск через celery beat раз в день в 05:00 UTC (08:00 МСК).
    
    Логика распределения для аккаунтов:
    - Сначала все чаты первого объекта, потом второго и т.д.
    - Задачи группируются по аккаунтам
    - Расписание рассчитывается с учетом режима аккаунта и интервалов
    """
    from app import app
    from app.models.account_publication_queue import AccountPublicationQueue
    from app.models.object import Object as AppObject
    from app.models.chat import Chat as AppChat
    from app.models.autopublish_config import AutopublishConfig as AppAutopublishConfig
    from app.models.telegram_account import TelegramAccount as AppTelegramAccount
    from app.utils.account_publication_utils import calculate_scheduled_times_for_account
    
    try:
        with app.app_context():
            # Через бота: создаем задачи в publication_queues
            configs = db.session.query(AutopublishConfig).filter_by(enabled=True).all()
            created_bot_queues = 0

            for cfg in configs:
                obj = db.session.query(Object).filter_by(object_id=cfg.object_id).first()
                if not obj:
                    continue

                # Не публикуем архивные объекты
                if obj.status == 'архив':
                    continue

                # Через бота: чаты подбираются автоматически
                if cfg.bot_enabled:
                    chats = _get_matching_bot_chats_for_object(db.session, obj)
                    # Получаем время для публикации (8:00-22:00 МСК)
                    now_msk = get_moscow_time()
                    scheduled_time_msk = get_next_allowed_time_msk(now_msk)
                    
                    # Конвертируем МСК время в UTC
                    scheduled_time_utc = msk_to_utc(scheduled_time_msk)
                    
                    for chat in chats:
                        queue = PublicationQueue(
                            object_id=obj.object_id,
                            chat_id=chat.chat_id,
                            account_id=None,
                            user_id=obj.user_id,
                            type='bot',
                            mode='autopublish',
                            status='pending',
                            scheduled_time=scheduled_time_utc,
                            created_at=datetime.utcnow(),
                        )
                        db.session.add(queue)
                        created_bot_queues += 1

            db.session.commit()
            logger.info(f"schedule_daily_autopublish: created {created_bot_queues} bot queue items")
            
            # Через аккаунты: создаем задачи в account_publication_queues
            from app.models.account_publication_queue import AccountPublicationQueue
            from app.models.autopublish_config import AutopublishConfig as AppAutopublishConfig
            from app.models.object import Object as AppObject
            
            app_configs = AppAutopublishConfig.query.filter_by(enabled=True).all()
            logger.info(f"schedule_daily_autopublish: Found {len(app_configs)} enabled autopublish configs")
            created_account_queues = 0
            
            # Группируем задачи по аккаунтам
            # Структура: {account_id: [(object_id, chat_id, user_id), ...]}
            # ВАЖНО: задачи добавляются в порядке объектов - сначала все чаты первого объекта, потом второго
            account_tasks = {}  # {account_id: [(object_id, chat_id, user_id), ...]}
            
            for cfg in app_configs:
                obj = AppObject.query.filter_by(object_id=cfg.object_id).first()
                if not obj or obj.status == 'архив':
                    logger.debug(f"schedule_daily_autopublish: Skipping object {cfg.object_id} - not found or archived")
                    continue
                
                accounts_cfg = getattr(cfg, 'accounts_config_json', None) or {}
                accounts_list = accounts_cfg.get('accounts') if isinstance(accounts_cfg, dict) else None
                
                if not accounts_list or not isinstance(accounts_list, list):
                    logger.debug(f"schedule_daily_autopublish: Object {cfg.object_id} has no accounts_config_json.accounts")
                    continue
                
                if accounts_list and isinstance(accounts_list, list):
                    for acc_entry in accounts_list:
                        try:
                            account_id = int(acc_entry.get('account_id'))
                        except Exception:
                            continue
                        chat_ids = acc_entry.get('chat_ids') or []
                        if not chat_ids:
                            continue
                        
                        # Проверяем, что аккаунт существует и активен
                        account = AppTelegramAccount.query.get(account_id)
                        if not account or not account.is_active:
                            continue
                        
                        # Ограничиваемся чатами этого аккаунта
                        # Проверяем обе связи: legacy (owner_account_id) и новая (TelegramAccountChat)
                        # Получаем chat_id из новой таблицы TelegramAccountChat
                        linked_chat_ids = [
                            link.chat_id for link in 
                            AppTelegramAccountChat.query.filter_by(account_id=account_id).all()
                        ]
                        
                        # Ищем чаты, которые либо:
                        # 1. Имеют owner_account_id == account_id (legacy)
                        # 2. Или связаны через TelegramAccountChat (новая связь)
                        user_chats = AppChat.query.filter(
                            AppChat.owner_type == 'user',
                            AppChat.chat_id.in_(chat_ids),
                            AppChat.is_active == True,
                            or_(
                                AppChat.owner_account_id == account_id,  # Legacy связь
                                AppChat.chat_id.in_(linked_chat_ids)  # Новая связь через TelegramAccountChat
                            )
                        ).all()
                        
                        if not user_chats:
                            logger.warning(f"schedule_daily_autopublish: No valid chats found for account {account_id} and object {obj.object_id}. chat_ids in config: {chat_ids}")
                            continue
                        
                        if account_id not in account_tasks:
                            account_tasks[account_id] = []
                        
                        # Добавляем все чаты этого объекта для этого аккаунта
                        # Порядок важен: сначала все чаты первого объекта, потом второго
                        for chat in user_chats:
                            account_tasks[account_id].append((obj.object_id, chat.chat_id, obj.user_id))
                            logger.debug(f"schedule_daily_autopublish: Added task for account {account_id}, object {obj.object_id}, chat {chat.chat_id}")
            
            # Создаем задачи для каждого аккаунта с учетом режима и лимитов
            now_msk = get_moscow_time()
            start_time_msk = now_msk.replace(hour=8, minute=0, second=0, microsecond=0)
            
            for account_id, tasks_list in account_tasks.items():
                account = AppTelegramAccount.query.get(account_id)
                if not account or not account.is_active:
                    continue
                
                # Получаем fix_interval_minutes для режима 'fix'
                fix_interval = getattr(account, 'fix_interval_minutes', None) if account.mode == 'fix' else None
                
                # Рассчитываем расписание для этого аккаунта
                scheduled_times = calculate_scheduled_times_for_account(
                    mode=account.mode,
                    total_tasks=len(tasks_list),
                    daily_limit=account.daily_limit,
                    start_time_msk=start_time_msk,
                    fix_interval=fix_interval
                )
                
                logger.info(f"Account {account_id} ({account.phone}): mode={account.mode}, tasks={len(tasks_list)}, scheduled_times={len(scheduled_times)}")
                
                # Создаем задачи с рассчитанным временем
                for i, (object_id, chat_id, user_id) in enumerate(tasks_list):
                    if i < len(scheduled_times):
                        scheduled_time_utc = msk_to_utc(scheduled_times[i])
                        
                        queue = AccountPublicationQueue(
                            object_id=object_id,
                            chat_id=chat_id,
                            account_id=account_id,
                            user_id=user_id,
                            status='pending',
                            scheduled_time=scheduled_time_utc,
                            created_at=datetime.utcnow(),
                        )
                        app_db.session.add(queue)
                        created_account_queues += 1
            
            app_db.session.commit()
            logger.info(f"schedule_daily_autopublish: created {created_account_queues} account queue items for {len(account_tasks)} accounts")
            
            if created_account_queues == 0:
                logger.warning("schedule_daily_autopublish: No account queue items created! Check configs and chat-account links.")
        
        return created_bot_queues + created_account_queues
    except Exception as e:
        logger.error(f"Error in schedule_daily_autopublish: {e}", exc_info=True)
        try:
            with app.app_context():
                db.session.rollback()
                app_db.session.rollback()
        except Exception:
            pass
        return 0


