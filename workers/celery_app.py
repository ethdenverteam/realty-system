"""
Celery application configuration
"""
from celery import Celery
from celery.schedules import crontab
import os

# Redis URL for Celery
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Create Celery app
celery_app = Celery(
    'realty_workers',
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    beat_schedule={
        'process-scheduled-publications-every-minute': {
            'task': 'workers.tasks.process_scheduled_publications',
            'schedule': 60.0,
        },
        'process-autopublish-every-minute': {
            'task': 'workers.tasks.process_autopublish',
            'schedule': 60.0,
        },
        # Ежедневное создание задач автопубликации (09:00 МСК ~= 06:00 UTC)
        'schedule-daily-autopublish-9-msk': {
            'task': 'workers.tasks.schedule_daily_autopublish',
            'schedule': crontab(minute=0, hour=6),
        },
    },
)

# Import tasks
from workers import tasks

