"""
Celery tasks for scheduled publications
Логика: обработка запланированных публикаций
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

@celery_app.task(name='workers.tasks.process_scheduled_publications')
def process_scheduled_publications():
    """Process scheduled publications"""
    from app import app
    try:
        with app.app_context():
            now = datetime.utcnow()
            
            # Get scheduled tasks ready to publish
            # Используем явный список полей для избежания NotImplementedError
            queues = db.session.query(PublicationQueue).filter(
                PublicationQueue.mode == 'scheduled',
                PublicationQueue.status == 'pending',
                PublicationQueue.scheduled_time <= now
            ).all()
            
            for queue in queues:
                publish_to_telegram.delay(queue.queue_id)
            
            return len(queues)
    except Exception as e:
        logger.error(f"Error processing scheduled publications: {e}", exc_info=True)
        return 0


