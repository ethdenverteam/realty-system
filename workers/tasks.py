"""
Фоновые задачи Celery для обработки публикаций
Цель: асинхронная публикация объектов в Telegram, обработка очередей, автопубликация
Логика: все задачи логируются для отслеживания выполнения и диагностики ошибок
"""
from workers.celery_app import celery_app
from app.database import db
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
            # Проверяем настройку обхода ограничения времени для админа (через app контекст)
            from app import app
            admin_bypass_enabled = False
            is_admin = False
            
            with app.app_context():
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
            queue.status = 'failed'
            queue.error_message = str(e)
            db.session.commit()
            return False
        
        except Exception as e:
            logger.error(f"Error publishing to Telegram: {e}")
            if queue:
                queue.status = 'failed'
                queue.error_message = str(e)
                queue.attempts += 1
                db.session.commit()
            return False
        finally:


@celery_app.task(name='workers.tasks.process_autopublish')
def process_autopublish():
    """Process autopublish queue - обрабатывает задачи в порядке scheduled_time"""
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
        with app.app_context():
            from app.models.account_publication_queue import AccountPublicationQueue
            from app.models.autopublish_config import AutopublishConfig as AppAutopublishConfig
            from app.models.object import Object as AppObject
            
            app_configs = AppAutopublishConfig.query.filter_by(enabled=True).all()
            created_account_queues = 0
            
            # Группируем задачи по аккаунтам
            # Структура: {account_id: [(object_id, chat_id, user_id), ...]}
            # ВАЖНО: задачи добавляются в порядке объектов - сначала все чаты первого объекта, потом второго
            account_tasks = {}  # {account_id: [(object_id, chat_id, user_id), ...]}
            
            for cfg in app_configs:
                obj = AppObject.query.filter_by(object_id=cfg.object_id).first()
                if not obj or obj.status == 'архив':
                    continue
                
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
                        account = AppTelegramAccount.query.get(account_id)
                        if not account or not account.is_active:
                            continue
                        
                        # Ограничиваемся чатами этого аккаунта
                        user_chats = AppChat.query.filter(
                            AppChat.owner_type == 'user',
                            AppChat.owner_account_id == account_id,
                            AppChat.chat_id.in_(chat_ids),
                            AppChat.is_active == True,
                        ).all()
                        
                        if account_id not in account_tasks:
                            account_tasks[account_id] = []
                        
                        # Добавляем все чаты этого объекта для этого аккаунта
                        # Порядок важен: сначала все чаты первого объекта, потом второго
                        for chat in user_chats:
                            account_tasks[account_id].append((obj.object_id, chat.chat_id, obj.user_id))
            
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
            logger.info(f"schedule_daily_autopublish: created {created_account_queues} account queue items")
        
        return created_bot_queues + created_account_queues
    except Exception as e:
        logger.error(f"Error in schedule_daily_autopublish: {e}", exc_info=True)
        db.session.rollback()
        try:
            with app.app_context():
                app_db.session.rollback()
        except:
            pass
        return 0


@celery_app.task(name='workers.tasks.process_scheduled_publications')
def process_scheduled_publications():
    """Process scheduled publications"""
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
            # Используем явный запрос через app_db для избежания проблем с закрытыми результатами
            tasks_query = app_db.session.query(ChatSubscriptionTask).filter(
                ChatSubscriptionTask.status.in_(['pending', 'processing', 'flood_wait']),
                or_(ChatSubscriptionTask.next_run_at.is_(None), ChatSubscriptionTask.next_run_at <= now),
            )
            tasks = tasks_query.all()

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
            chat_links_raw = task.chat_links or []
            
            # Преобразуем в список строк (поддерживаем старый формат - массив строк, и новый - массив объектов)
            chat_links = []
            for item in chat_links_raw:
                if isinstance(item, str):
                    chat_links.append(item)
                elif isinstance(item, dict):
                    link = item.get('link', '')
                    if link:
                        chat_links.append(link)
                else:
                    logger.warning(f"Unexpected chat_link format in task {task_id}: {type(item)}")
            
            # Начинаем подписку с current_index
            current_index = task.current_index
            total_chats = task.total_chats
            successful_count = task.successful_count
            flood_count = task.flood_count
            
            logger.info(f"Starting subscription task {task_id}: {current_index}/{total_chats} chats, account: {account.phone}")
            
            # Подписываемся на текущий чат
            if current_index >= len(chat_links) or current_index >= total_chats:
                # Все чаты обработаны
                task.status = 'completed'
                task.completed_at = datetime.utcnow()
                task.result = f"Успешная подписка {successful_count}/{total_chats}"
                app_db.session.commit()
                logger.info(f"Task {task_id} completed: {successful_count}/{total_chats} chats subscribed")
                return True
            
            chat_link = chat_links[current_index]
            # Убеждаемся что chat_link - строка
            if not isinstance(chat_link, str):
                chat_link = str(chat_link)
            logger.info(f"Subscribing to chat {current_index + 1}/{total_chats}: {chat_link[:50] if len(chat_link) > 50 else chat_link}...")
            
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

                # Ищем существующий чат (чат в БД должен быть один на telegram_chat_id)
                existing_chat = AppChat.query.filter_by(telegram_chat_id=telegram_chat_id).first()

                if existing_chat:
                    # Обновляем название только если его еще нет или оно временное
                    if (
                        not existing_chat.title
                        or existing_chat.title.startswith('Chat ')
                        or existing_chat.title.startswith('invite_')
                        or existing_chat.title.startswith('public_')
                    ):
                        existing_chat.title = title
                    existing_chat.type = chat_type
                    existing_chat.is_active = True
                    app_db.session.commit()
                    chat_obj = existing_chat
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
                    chat_obj = new_chat

                # Создаем/обновляем связь аккаунт ↔ чат в таблице TelegramAccountChat
                if chat_obj and chat_obj.chat_id:
                    link = AppTelegramAccountChat.query.filter_by(
                        account_id=account.account_id,
                        chat_id=chat_obj.chat_id,
                    ).first()
                    if not link:
                        link = AppTelegramAccountChat(
                            account_id=account.account_id,
                            chat_id=chat_obj.chat_id,
                        )
                        app_db.session.add(link)
                        app_db.session.commit()
                
                # Обновляем информацию о чате в ChatGroup (сохраняем telegram_chat_id и title)
                if task.group_id:
                    group = AppChatGroup.query.get(task.group_id)
                    if group:
                        group.update_chat_link_info(
                            link=chat_link,
                            telegram_chat_id=telegram_chat_id,
                            title=title
                        )
                        app_db.session.commit()
                        logger.info(f"Updated chat info in ChatGroup {task.group_id} for link {chat_link[:50]}...")
                
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
    
    with app.app_context():
        try:
            now = datetime.utcnow()
            
            # Получаем настройку проверки дубликатов
            duplicates_setting = app_db.session.query(SystemSetting).filter_by(key='allow_duplicates').first()
            allow_duplicates = False
            if duplicates_setting and isinstance(duplicates_setting.value_json, dict):
                allow_duplicates = duplicates_setting.value_json.get('enabled', False)
            
            # Получаем все активные аккаунты
            accounts = app_db.session.query(AppTelegramAccount).filter_by(is_active=True).all()
            
            processed_count = 0
            
            for account in accounts:
                # Проверяем лимит аккаунта (по успешным публикациям за сегодня)
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                today_publications = app_db.session.query(AppPublicationHistory).filter(
                    AppPublicationHistory.account_id == account.account_id,
                    AppPublicationHistory.published_at >= today_start,
                    AppPublicationHistory.deleted == False
                ).count()
                
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
                    try:
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
                        logger.info(f"Successfully published object {obj.object_id} via account {account.account_id} to chat {chat.telegram_chat_id}")
                        
                    except Exception as e:
                        logger.error(f"Error processing queue {queue.queue_id} for account {account.account_id}: {e}", exc_info=True)
                        queue.status = 'failed'
                        queue.error_message = str(e)
                        queue.attempts += 1
                        app_db.session.commit()
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
            
        except Exception as e:
            logger.error(f"Error in process_account_autopublish: {e}", exc_info=True)
            return 0

