"""
AccountPublicationQueue model - Очереди публикаций для Telegram аккаунтов пользователей
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship


class AccountPublicationQueue(db.Model):
    """AccountPublicationQueue model - Очереди публикаций для аккаунтов"""
    __tablename__ = 'account_publication_queues'
    
    queue_id = Column(Integer, primary_key=True, autoincrement=True)
    object_id = Column(String(50), ForeignKey('objects.object_id'), nullable=False, index=True)
    chat_id = Column(Integer, ForeignKey('chats.chat_id'), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey('telegram_accounts.account_id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=True, index=True)
    status = Column(String(20), default='pending', nullable=False)  # pending/processing/completed/failed/retrying/flood_wait
    scheduled_time = Column(DateTime, nullable=False, index=True)  # Время публикации (UTC)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    message_id = Column(String(50), nullable=True)  # Telegram message ID
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    object = relationship('Object', back_populates='account_publication_queues')
    chat = relationship('Chat', back_populates='account_publication_queues')
    account = relationship('TelegramAccount', back_populates='account_publication_queues')
    user = relationship('User', back_populates='account_publication_queues')
    
    def __repr__(self):
        return f'<AccountPublicationQueue {self.queue_id} (account: {self.account_id}, status: {self.status})>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'queue_id': self.queue_id,
            'object_id': self.object_id,
            'chat_id': self.chat_id,
            'account_id': self.account_id,
            'user_id': self.user_id,
            'status': self.status,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'attempts': self.attempts,
            'error_message': self.error_message,
            'message_id': self.message_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

