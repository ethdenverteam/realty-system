"""
Chat model - Чаты для публикации
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship


class Chat(db.Model):
    """Chat model - Чаты для публикации объявлений"""
    __tablename__ = 'chats'
    
    chat_id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_chat_id = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    type = Column(String(20), nullable=False)  # group/channel/supergroup
    category = Column(String(100), nullable=True)  # rooms_1k/rooms_2k/district_center/price_4000_6000 (legacy)
    filters_json = Column(JSON, nullable=True)  # Extended filters: {rooms_types: [], districts: [], price_min: 0, price_max: 0}
    owner_type = Column(String(10), default='bot', nullable=False)  # bot/user
    owner_account_id = Column(Integer, ForeignKey('telegram_accounts.account_id'), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    members_count = Column(Integer, default=0, nullable=False)
    added_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_publication = Column(DateTime, nullable=True)
    total_publications = Column(Integer, default=0, nullable=False)
    
    # Relationships
    account = relationship('TelegramAccount', back_populates='chats')
    publication_queues = relationship('PublicationQueue', back_populates='chat')
    publication_history = relationship('PublicationHistory', back_populates='chat')
    
    def __repr__(self):
        return f'<Chat {self.telegram_chat_id} ({self.title})>'
    
    def to_dict(self):
        """Convert to dictionary"""
        result = {
            'chat_id': self.chat_id,
            'telegram_chat_id': self.telegram_chat_id,
            'title': self.title,
            'type': self.type,
            'category': self.category,
            'owner_type': self.owner_type,
            'owner_account_id': self.owner_account_id,
            'is_active': self.is_active,
            'members_count': self.members_count,
            'added_date': self.added_date.isoformat() if self.added_date else None,
            'last_publication': self.last_publication.isoformat() if self.last_publication else None,
            'total_publications': self.total_publications,
        }
        # Safely handle filters_json - it might not exist in the database
        try:
            result['filters_json'] = self.filters_json or {}
        except AttributeError:
            # Column doesn't exist in database
            result['filters_json'] = {}
        return result

