"""
Celery tasks for background processing
"""
from workers.celery_app import celery_app
from bot.database import get_db
from bot.models import PublicationQueue, Object, Chat, PublicationHistory, AutopublishConfig, TelegramAccount
from datetime import datetime, timedelta
import logging

from bot.utils import get_districts_config

logger = logging.getLogger(__name__)


@celery_app.task(name='workers.tasks.publish_to_telegram')
def publish_to_telegram(queue_id: int):
    """Publish object to Telegram chat"""
    db = get_db()
    try:
        queue = db.query(PublicationQueue).get(queue_id)
        if not queue:
            logger.error(f"Queue {queue_id} not found")
            return False
        
        # Update status
        queue.status = 'processing'
        queue.started_at = datetime.utcnow()
        db.commit()
        
        # Get object and chat
        obj = db.query(Object).get(queue.object_id)
        chat = db.query(Chat).get(queue.chat_id)
        
        if not obj or not chat:
            queue.status = 'failed'
            queue.error_message = 'Object or chat not found'
            db.commit()
            return False
        
        # Check if object was published to this chat within last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_publication = db.query(PublicationHistory).filter(
            PublicationHistory.object_id == queue.object_id,
            PublicationHistory.chat_id == queue.chat_id,
            PublicationHistory.published_at >= yesterday,
            PublicationHistory.deleted == False
        ).first()
        
        if recent_publication:
            logger.info(f"Object {queue.object_id} was already published to chat {queue.chat_id} within 24 hours, skipping")
            queue.status = 'failed'
            queue.error_message = 'Object was already published to this chat within 24 hours'
            db.commit()
            return False
        
        # TODO: Implement actual Telegram publishing
        # This is a placeholder
        logger.info(f"Publishing object {obj.object_id} to chat {chat.telegram_chat_id}")
        
        # Simulate success
        queue.status = 'completed'
        queue.completed_at = datetime.utcnow()
        queue.message_id = '12345'  # Placeholder
        
        # Create history entry
        history = PublicationHistory(
            queue_id=queue_id,
            object_id=obj.object_id,
            chat_id=chat.chat_id,
            account_id=queue.account_id,
            published_at=datetime.utcnow(),
            message_id=queue.message_id
        )
        db.add(history)
        
        # Update chat stats
        chat.total_publications += 1
        chat.last_publication = datetime.utcnow()
        
        db.commit()
        
        return True
        
    except Exception as e:
        logger.error(f"Error publishing to Telegram: {e}")
        if queue:
            queue.status = 'failed'
            queue.error_message = str(e)
            queue.attempts += 1
            db.commit()
        return False
    finally:
        db.close()


@celery_app.task(name='workers.tasks.process_autopublish')
def process_autopublish():
    """Process autopublish queue"""
    db = get_db()
    try:
        # Get pending autopublish tasks
        queues = db.query(PublicationQueue).filter(
            PublicationQueue.mode == 'autopublish',
            PublicationQueue.status == 'pending'
        ).all()
        
        for queue in queues:
            publish_to_telegram.delay(queue.queue_id)
        
        return len(queues)
    finally:
        db.close()


def _get_matching_bot_chats_for_object(db, obj: Object):
    """
    Подбор чатов бота для объекта по тем же правилам,
    что и ручная публикация через бота.
    """
    target_chats = []

    chats = db.query(Chat).filter_by(owner_type='bot', is_active=True).all()

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

    Предполагается запуск через celery beat раз в день в 06:00 UTC (09:00 МСК).
    """
    db = get_db()
    try:
        configs = db.query(AutopublishConfig).filter_by(enabled=True).all()
        created_queues = 0

        for cfg in configs:
            obj = db.query(Object).filter_by(object_id=cfg.object_id).first()
            if not obj:
                continue

            # Не публикуем архивные объекты
            if obj.status == 'архив':
                continue

            # Через бота: чаты подбираются автоматически
            if cfg.bot_enabled:
                chats = _get_matching_bot_chats_for_object(db, obj)
                for chat in chats:
                    queue = PublicationQueue(
                        object_id=obj.object_id,
                        chat_id=chat.chat_id,
                        account_id=None,
                        user_id=obj.user_id,
                        type='bot',
                        mode='autopublish',
                        status='pending',
                        created_at=datetime.utcnow(),
                    )
                    db.add(queue)
                    created_queues += 1

            # Автопубликация через аккаунты пользователей (accounts_config_json)
            accounts_cfg = getattr(cfg, 'accounts_config_json', None) or {}
            accounts_list = accounts_cfg.get('accounts') if isinstance(accounts_cfg, dict) else None

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
                    account = db.query(TelegramAccount).get(account_id)
                    if not account or not account.is_active:
                        continue

                    # Ограничиваемся чатами этого аккаунта
                    user_chats = db.query(Chat).filter(
                        Chat.owner_type == 'user',
                        Chat.owner_account_id == account_id,
                        Chat.chat_id.in_(chat_ids),
                        Chat.is_active == True,
                    ).all()

                    for chat in user_chats:
                        queue = PublicationQueue(
                            object_id=obj.object_id,
                            chat_id=chat.chat_id,
                            account_id=account_id,
                            user_id=obj.user_id,
                            type='user',
                            mode='autopublish',
                            status='pending',
                            created_at=datetime.utcnow(),
                        )
                        db.add(queue)
                        created_queues += 1

        db.commit()
        logger.info(f"schedule_daily_autopublish: created {created_queues} queue items")
        return created_queues
    except Exception as e:
        logger.error(f"Error in schedule_daily_autopublish: {e}", exc_info=True)
        db.rollback()
        return 0
    finally:
        db.close()


@celery_app.task(name='workers.tasks.process_scheduled_publications')
def process_scheduled_publications():
    """Process scheduled publications"""
    db = get_db()
    try:
        now = datetime.utcnow()
        
        # Get scheduled tasks ready to publish
        queues = db.query(PublicationQueue).filter(
            PublicationQueue.mode == 'scheduled',
            PublicationQueue.status == 'pending',
            PublicationQueue.scheduled_time <= now
        ).all()
        
        for queue in queues:
            publish_to_telegram.delay(queue.queue_id)
        
        return len(queues)
    finally:
        db.close()

