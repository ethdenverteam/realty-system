"""
ChatSubscriptionTask model - Задачи подписки на чаты
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship


class ChatSubscriptionTask(db.Model):
    """ChatSubscriptionTask model - Задачи подписки на списки чатов"""
    __tablename__ = 'chat_subscription_tasks'
    
    task_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey('telegram_accounts.account_id'), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey('chat_groups.group_id'), nullable=False, index=True)
    
    # Статус задачи: pending/processing/completed/failed/flood_wait
    status = Column(String(20), default='pending', nullable=False, index=True)
    
    # Прогресс подписки
    current_index = Column(Integer, default=0, nullable=False)  # На каком чате остановились (индекс в списке)
    total_chats = Column(Integer, nullable=False)  # Всего чатов в списке
    successful_count = Column(Integer, default=0, nullable=False)  # Успешно подписано
    
    # Обработка flood ошибок
    flood_count = Column(Integer, default=0, nullable=False)  # Количество flood ошибок
    flood_wait_until = Column(DateTime, nullable=True)  # До какого времени ждем после flood
    # Режим интервала: safe/aggressive (safe=10 минут, aggressive=2 минуты)
    interval_mode = Column(String(20), default='safe', nullable=False)
    # Следующий запуск задачи (UTC) для устойчивого планирования через Celery beat
    next_run_at = Column(DateTime, nullable=True, index=True)
    
    # Результат подписки
    result = Column(Text, nullable=True)  # Текст результата (flood + время + место или успешная подписка n/n)
    error_message = Column(Text, nullable=True)  # Сообщение об ошибке
    
    # Временные метки
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # Расчетное время завершения (UTC)
    estimated_completion = Column(DateTime, nullable=True)
    
    # Список ссылок на чаты (JSON массив строк)
    chat_links = Column(JSON, nullable=False)  # ["https://t.me/+...", ...]
    
    # Relationships
    user = relationship('User')
    account = relationship('TelegramAccount')
    group = relationship('ChatGroup')
    
    def __repr__(self):
        return f'<ChatSubscriptionTask {self.task_id} (status: {self.status}, progress: {self.successful_count}/{self.total_chats})>'
    
    def to_dict(self):
        """Convert to dictionary"""
        # Рассчитываем расчетное время завершения (по МСК)
        estimated_completion = None
        if hasattr(self, 'estimated_completion') and self.estimated_completion:
            # Если есть сохраненное значение - используем его
            from app.utils.time_utils import utc_to_msk
            estimated_completion_msk = utc_to_msk(self.estimated_completion)
            estimated_completion = estimated_completion_msk.strftime('%Y-%m-%d %H:%M:%S МСК')
        elif self.status in ['pending', 'processing'] and self.current_index < self.total_chats:
            # Рассчитываем динамически на основе оставшихся чатов
            remaining = self.total_chats - self.current_index
            from datetime import timedelta
            from app.utils.time_utils import utc_to_msk
            # Базовый интервал в секундах: safe=10 мин (600 сек), aggressive=2 мин (120 сек)
            base_minutes = 10 if getattr(self, 'interval_mode', 'safe') == 'safe' else 2
            base_seconds = base_minutes * 60
            # Среднее время случайной переменной (1-99 секунд) = 50 секунд
            average_jitter = 50
            # Время на один чат = базовый интервал + средний джиттер
            time_per_chat = base_seconds + average_jitter
            # Общее время = время на чат * количество оставшихся чатов
            total_seconds = time_per_chat * remaining
            
            # Используем текущее время или время начала
            base_time = self.started_at if self.started_at else datetime.utcnow()
            estimated_completion_utc = base_time + timedelta(seconds=total_seconds)
            estimated_completion_msk = utc_to_msk(estimated_completion_utc)
            estimated_completion = estimated_completion_msk.strftime('%Y-%m-%d %H:%M:%S МСК')
        
        return {
            'task_id': self.task_id,
            'user_id': self.user_id,
            'account_id': self.account_id,
            'group_id': self.group_id,
            'status': self.status,
            'current_index': self.current_index,
            'total_chats': self.total_chats,
            'successful_count': self.successful_count,
            'flood_count': self.flood_count,
            'flood_wait_until': self.flood_wait_until.isoformat() if self.flood_wait_until else None,
            'interval_mode': self.interval_mode,
            'result': self.result,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'chat_links': self.chat_links or [],
            'estimated_completion': estimated_completion,
            'next_run_at': self.next_run_at.isoformat() if self.next_run_at else None,
        }

