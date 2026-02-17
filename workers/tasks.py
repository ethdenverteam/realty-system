"""
Фоновые задачи Celery для обработки публикаций
Цель: асинхронная публикация объектов в Telegram, обработка очередей, автопубликация
Логика: все задачи логируются для отслеживания выполнения и диагностики ошибок
"""
from workers.celery_app import celery_app
from bot.database import get_db
from bot.models import PublicationQueue, Object, Chat, PublicationHistory, AutopublishConfig, TelegramAccount
from datetime import datetime, timedelta
from sqlalchemy import or_
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
from app.models.telegram_account import TelegramAccount as AppTelegramAccount

logger = logging.getLogger(__name__)


@celery_app.task(name='workers.tasks.publish_to_telegram')
def publish_to_telegram(queue_id: int):
    """
    Публикация объекта недвижимости в Telegram чат
    Логика: проверка дубликатов (24 часа), форматирование текста, отправка через API, создание истории
    Все этапы логируются для отслеживания процесса публикации
    """
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
        
        # Проверка времени для автопубликации: публикация разрешена только с 8:00 до 22:00 МСК
        if queue.mode == 'autopublish':
            now_msk = get_moscow_time()
            if not is_within_publish_hours(now_msk):
                logger.info(f"Outside publish hours (8:00-22:00 МСК), rescheduling queue {queue_id}")
                # Переносим на ближайшее разрешенное время
                next_time_msk = get_next_allowed_time_msk(now_msk)
                next_time_utc = msk_to_utc(next_time_msk)
                queue.scheduled_time = next_time_utc
                queue.status = 'pending'
                db.commit()
                return False
        
        # Check if object was published to this chat within last 24 hours
        # Ограничение 24 часа применяется только для ручной публикации (mode != 'autopublish')
        # Для автопубликации ограничение не применяется
        if queue.mode != 'autopublish':
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
            db.commit()
            return False
        
        # Получаем пользователя бота для форматирования текста
        bot_user = None
        if obj.user_id:
            bot_user = db.query(BotUser).filter_by(user_id=obj.user_id).first()
        
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
        
        # Отправляем сообщение
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
        payload = {
            'chat_id': chat.telegram_chat_id,
            'text': publication_text,
            'parse_mode': 'HTML'
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if not result.get('ok'):
                error_description = result.get('description', 'Unknown error')
                logger.error(f"Failed to publish: {error_description}")
                queue.status = 'failed'
                queue.error_message = error_description
                db.commit()
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
            db.add(history)
            
            # Обновляем статистику чата
            chat.total_publications = (chat.total_publications or 0) + 1
            chat.last_publication = datetime.utcnow()
            
            db.commit()
            
            # Создаем задачу на следующий день для автопубликации
            if queue.mode == 'autopublish':
                # Получаем время для следующей публикации (следующий день, начиная с 8:00 МСК)
                now_msk = get_moscow_time()
                next_time_msk = get_next_scheduled_time_for_publication(now_msk)
                # Конвертируем МСК время в UTC для сохранения в БД
                try:
                    from app.utils.time_utils import msk_to_utc
                    next_time_utc = msk_to_utc(next_time_msk)
                except ImportError:
                    # Fallback если импорт не удался
                    try:
                        from zoneinfo import ZoneInfo
                        MOSCOW_TZ = ZoneInfo('Europe/Moscow')
                        UTC_TZ = ZoneInfo('UTC')
                    except ImportError:
                        import pytz
                        MOSCOW_TZ = pytz.timezone('Europe/Moscow')
                        UTC_TZ = pytz.timezone('UTC')
                    
                    next_time_with_tz = next_time_msk.replace(tzinfo=MOSCOW_TZ)
                    next_time_utc = next_time_with_tz.astimezone(UTC_TZ).replace(tzinfo=None)
                
                # Создаем новую задачу на следующий день
                next_queue = PublicationQueue(
                    object_id=obj.object_id,
                    chat_id=chat.chat_id,
                    account_id=queue.account_id,
                    user_id=queue.user_id,
                    type=queue.type,
                    mode='autopublish',
                    status='pending',
                    scheduled_time=next_time_utc,
                    created_at=datetime.utcnow(),
                )
                db.add(next_queue)
                db.commit()
                logger.info(f"Created next day autopublish task for object {obj.object_id} to chat {chat.chat_id} at {next_time_msk}")
            
            logger.info(f"Successfully published object {obj.object_id} to chat {chat.telegram_chat_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending message to Telegram: {e}")
            queue.status = 'failed'
            queue.error_message = str(e)
            db.commit()
            return False
        
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
    """Process autopublish queue - обрабатывает задачи в порядке scheduled_time"""
    db = get_db()
    try:
        now = datetime.utcnow()
        
        # Get pending autopublish tasks that are ready to publish
        # Сортируем по scheduled_time (старейшие первыми), если scheduled_time не установлено - по created_at
        queues = db.query(PublicationQueue).filter(
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
            logger.info(f"Publishing queue {queue.queue_id} for object {queue.object_id} to chat {queue.chat_id} (scheduled: {scheduled_str}, created: {queue.created_at})")
            publish_to_telegram.delay(queue.queue_id)
        
        return len(queues)
    except Exception as e:
        logger.error(f"Error processing autopublish queue: {e}", exc_info=True)
        return 0
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


@celery_app.task(name='workers.tasks.process_chat_subscriptions')
def process_chat_subscriptions():
    """
    Process chat subscriptions based on next_run_at (устойчивая к перезапуску схема).
    Выбирает задачи из app БД и запускает шаг подписки через subscribe_to_chats_task.
    """
    from app import app

    with app.app_context():
        try:
            now = datetime.utcnow()
            # Выбираем задачи, которые нужно выполнять сейчас или которые ещё не имеют next_run_at
            tasks = ChatSubscriptionTask.query.filter(
                ChatSubscriptionTask.status.in_(['pending', 'processing', 'flood_wait']),
                or_(ChatSubscriptionTask.next_run_at.is_(None), ChatSubscriptionTask.next_run_at <= now),
            ).all()

            if not tasks:
                return 0

            count = 0
            for task in tasks:
                logger.info(
                    f"Scheduling chat subscription step for task {task.task_id} "
                    f"(status={task.status}, current_index={task.current_index}/{task.total_chats}, "
                    f"next_run_at={task.next_run_at})"
                )
                subscribe_to_chats_task.delay(task.task_id)
                count += 1

            return count
        except Exception as e:
            logger.error(f"Error in process_chat_subscriptions: {e}", exc_info=True)
            return 0


@celery_app.task(name='workers.tasks.subscribe_to_chats_task')
def subscribe_to_chats_task(task_id: int):
    """
    Асинхронная подписка на список чатов
    Логика: подписывается на чаты по очереди с интервалом 10 минут, обрабатывает flood ошибки
    Первые 3 flood ошибки - ждем и продолжаем автоматически, после 3-го - останавливаем и сохраняем место
    """
    # Используем app database для доступа к моделям подписок
    from app import app
    
    with app.app_context():
        try:
            task = ChatSubscriptionTask.query.get(task_id)
            if not task:
                logger.error(f"ChatSubscriptionTask {task_id} not found")
                return False
            
            # Проверяем статус задачи
            if task.status not in ['pending', 'processing', 'flood_wait']:
                logger.info(f"Task {task_id} is not in pending/processing/flood_wait status: {task.status}")
                return False
            
            # Получаем аккаунт
            account = AppTelegramAccount.query.get(task.account_id)
            if not account:
                logger.error(f"TelegramAccount {task.account_id} not found")
                task.status = 'failed'
                task.error_message = 'Account not found'
                task.completed_at = datetime.utcnow()
                app_db.session.commit()
                return False
            
            # Если задача на паузе (ручной pause) и нет flood_wait_until - выходим
            if task.status == 'flood_wait' and task.flood_wait_until is None:
                logger.info(f"Task {task_id} is paused by user, skipping execution")
                return False

            # Обновляем статус на processing при первом запуске
            if task.status == 'pending':
                task.status = 'processing'
                task.started_at = datetime.utcnow()
                app_db.session.commit()
            
            # Получаем список ссылок
            chat_links = task.chat_links or []
            
            # Начинаем подписку с current_index
            current_index = task.current_index
            total_chats = task.total_chats
            successful_count = task.successful_count
            flood_count = task.flood_count
            
            logger.info(f"Starting subscription task {task_id}: {current_index}/{total_chats} chats, account: {account.phone}")
            
            # Подписываемся на текущий чат
            if current_index >= total_chats:
                # Все чаты обработаны
                task.status = 'completed'
                task.completed_at = datetime.utcnow()
                task.result = f"Успешная подписка {successful_count}/{total_chats}"
                app_db.session.commit()
                logger.info(f"Task {task_id} completed: {successful_count}/{total_chats} chats subscribed")
                return True
            
            chat_link = chat_links[current_index]
            logger.info(f"Subscribing to chat {current_index + 1}/{total_chats}: {chat_link[:50]}...")
            
            # Выполняем подписку
            success, error_msg, chat_info = run_async(subscribe_to_chat(account.phone, chat_link))
            
            if success and chat_info:
                # Успешная подписка
                successful_count += 1
                current_index += 1
                
                # Сохраняем или обновляем чат в БД
                telegram_chat_id = chat_info['telegram_chat_id']
                title = chat_info['title']
                chat_type = chat_info['type']
                
                # Ищем существующий чат
                existing_chat = AppChat.query.filter_by(telegram_chat_id=telegram_chat_id).first()
                
                if existing_chat:
                    # Обновляем название только если его еще нет или оно временное
                    if not existing_chat.title or existing_chat.title.startswith('Chat ') or existing_chat.title.startswith('invite_') or existing_chat.title.startswith('public_'):
                        existing_chat.title = title
                    existing_chat.type = chat_type
                    existing_chat.owner_account_id = account.account_id
                    existing_chat.is_active = True
                    app_db.session.commit()
                else:
                    # Создаем новый чат
                    new_chat = AppChat(
                        telegram_chat_id=telegram_chat_id,
                        title=title,
                        type=chat_type,
                        owner_type='user',
                        owner_account_id=account.account_id,
                        is_active=True,
                    )
                    app_db.session.add(new_chat)
                    app_db.session.commit()
                
                # Обновляем задачу
                task.current_index = current_index
                task.successful_count = successful_count
                task.flood_count = 0  # Сбрасываем счетчик flood при успехе
                app_db.session.commit()
                
                logger.info(f"Successfully subscribed to chat {current_index}/{total_chats}: {title}")
                
                # Определяем базовый интервал:
                # - 1 минута для уже подписанных чатов
                # - иначе по режиму interval_mode: safe=10 мин, aggressive=2 мин
                base_minutes = 10
                if chat_info.get('already_subscribed'):
                    base_minutes = 1
                else:
                    try:
                        if getattr(task, 'interval_mode', 'safe') == 'aggressive':
                            base_minutes = 2
                    except Exception:
                        pass
                
                # Добавляем случайный джиттер 1-99 секунд
                jitter_seconds = random.randint(1, 99)
                delay_seconds = base_minutes * 60 + jitter_seconds
                
                # Если это не последний чат, планируем следующую подписку через next_run_at
                if current_index < total_chats:
                    next_run = datetime.utcnow() + timedelta(seconds=delay_seconds)
                    task.next_run_at = next_run
                    app_db.session.commit()
                    logger.info(
                        f"Scheduled next subscription step for task {task_id} at {next_run} "
                        f"(base {base_minutes} min + jitter {jitter_seconds}s)"
                    )
                    return True
                else:
                    # Все чаты обработаны
                    task.status = 'completed'
                    task.completed_at = datetime.utcnow()
                    task.result = f"Успешная подписка {successful_count}/{total_chats}"
                    task.next_run_at = None
                    app_db.session.commit()
                    logger.info(f"Task {task_id} completed: {successful_count}/{total_chats} chats subscribed")
                    return True
                    
            elif error_msg and error_msg.startswith('FLOOD_WAIT:'):
                # Flood ошибка
                wait_seconds = int(error_msg.split(':')[1])
                flood_count += 1
                
                logger.warning(f"FloodWaitError for task {task_id}, chat {current_index + 1}/{total_chats}: wait {wait_seconds} seconds (flood count: {flood_count})")
                
                # Рассчитываем время окончания flood
                flood_wait_until = datetime.utcnow() + timedelta(seconds=wait_seconds)
                
                if flood_count <= 3:
                    # Первые 3 flood ошибки - ждем и продолжаем автоматически
                    task.flood_count = flood_count
                    task.flood_wait_until = flood_wait_until
                    task.status = 'processing'
                    task.next_run_at = flood_wait_until
                    app_db.session.commit()
                    
                    logger.info(
                        f"Task {task_id} will continue after flood wait ({wait_seconds}s) "
                        f"(auto-continue, flood count: {flood_count})"
                    )
                    return True
                else:
                    # После 3-го flood - останавливаем и сохраняем место
                    task.status = 'flood_wait'
                    task.flood_count = flood_count
                    task.flood_wait_until = flood_wait_until
                    task.current_index = current_index  # Сохраняем место остановки
                    task.result = f"Flood ошибка (flood count: {flood_count}), остановка на чате {current_index + 1}/{total_chats}, подождите до {flood_wait_until.strftime('%Y-%m-%d %H:%M:%S')} UTC"
                    task.next_run_at = None
                    app_db.session.commit()
                    logger.warning(f"Task {task_id} stopped due to flood (count: {flood_count}), stopped at chat {current_index + 1}/{total_chats}")
                    return False
            else:
                # Другая ошибка - логируем и продолжаем со следующего чата
                logger.error(f"Error subscribing to chat {current_index + 1}/{total_chats} for task {task_id}: {error_msg}")
                current_index += 1
                
                # Обновляем задачу
                task.current_index = current_index
                task.error_message = f"Ошибка на чате {current_index}/{total_chats}: {error_msg}"
                app_db.session.commit()
                
                # Определяем, является ли ошибка "ошибкой ссылки" (инвайт истёк, чат не найден, неверный формат)
                link_error = False
                if error_msg:
                    msg_lower = error_msg.lower()
                    if (
                        'invite link has expired' in msg_lower
                        or 'chat not found' in msg_lower
                        or 'invalid chat link format' in msg_lower
                    ):
                        link_error = True
                
                if link_error:
                    base_minutes = 1
                else:
                    base_minutes = 10
                    try:
                        if getattr(task, 'interval_mode', 'safe') == 'aggressive':
                            base_minutes = 2
                    except Exception:
                        pass
                jitter_seconds = random.randint(1, 99)
                delay_seconds = base_minutes * 60 + jitter_seconds
                
                # Продолжаем со следующего чата с задержкой через next_run_at
                if current_index < total_chats:
                    next_run = datetime.utcnow() + timedelta(seconds=delay_seconds)
                    task.next_run_at = next_run
                    app_db.session.commit()
                    logger.info(
                        f"Scheduled next subscription step after error for task {task_id} at {next_run} "
                        f"(base {base_minutes} min + jitter {jitter_seconds}s, link_error={link_error})"
                    )
                    return True
                else:
                    # Все чаты обработаны (с ошибками)
                    task.status = 'completed'
                    task.completed_at = datetime.utcnow()
                    task.result = f"Подписка завершена с ошибками: {successful_count}/{total_chats} успешно"
                    task.next_run_at = None
                    app_db.session.commit()
                    logger.info(f"Task {task_id} completed with errors: {successful_count}/{total_chats} chats subscribed")
                    return True
                    
        except Exception as e:
            logger.error(f"Error in subscribe_to_chats_task {task_id}: {e}", exc_info=True)
            try:
                task = ChatSubscriptionTask.query.get(task_id)
                if task:
                    task.status = 'failed'
                    task.error_message = f"Unexpected error: {str(e)}"
                    task.completed_at = datetime.utcnow()
                    app_db.session.commit()
            except:
                pass
            return False

