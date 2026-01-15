"""
PublicationHistory model - История публикаций
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship


class PublicationHistory(db.Model):
    """PublicationHistory model - История публикаций"""
    __tablename__ = 'publication_history'
    
    history_id = Column(Integer, primary_key=True, autoincrement=True)
    queue_id = Column(Integer, ForeignKey('publication_queues.queue_id'), nullable=True, index=True)
    object_id = Column(String(50), ForeignKey('objects.object_id'), nullable=False, index=True)
    chat_id = Column(Integer, ForeignKey('chats.chat_id'), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey('telegram_accounts.account_id'), nullable=True)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    message_id = Column(String(50), nullable=True)  # Telegram message ID
    deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    object = relationship('Object', back_populates='publication_history')
    chat = relationship('Chat', back_populates='publication_history')
    account = relationship('TelegramAccount', back_populates='publication_history')
    
    def __repr__(self):
        return f'<PublicationHistory {self.history_id} (object: {self.object_id})>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'history_id': self.history_id,
            'queue_id': self.queue_id,
            'object_id': self.object_id,
            'chat_id': self.chat_id,
            'account_id': self.account_id,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'message_id': self.message_id,
            'deleted': self.deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

