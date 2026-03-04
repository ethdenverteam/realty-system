"""
Celery tasks package
Логика: объединение всех Celery задач для импорта в celery_app
"""
# Импортируем все задачи для регистрации в Celery
from workers.tasks.tasks_publication import publish_to_telegram
from workers.tasks.tasks_autopublish import process_autopublish, schedule_daily_autopublish, _get_matching_bot_chats_for_object
from workers.tasks.tasks_scheduled import process_scheduled_publications
from workers.tasks.tasks_chat_subscriptions import process_chat_subscriptions, subscribe_to_chats_task
from workers.tasks.tasks_account_autopublish import process_account_autopublish

__all__ = [
    'publish_to_telegram',
    'process_autopublish',
    'schedule_daily_autopublish',
    '_get_matching_bot_chats_for_object',
    'process_scheduled_publications',
    'process_chat_subscriptions',
    'subscribe_to_chats_task',
    'process_account_autopublish',
]

