"""
Celery tasks for chat subscriptions
Логика: подписка на чаты через Telethon
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


