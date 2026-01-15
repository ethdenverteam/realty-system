"""
Celery application configuration
"""
from celery import Celery
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
)

# Import tasks
from workers import tasks

