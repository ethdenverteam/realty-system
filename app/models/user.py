"""
User model
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, JSON
from sqlalchemy.orm import relationship


class User(db.Model):
    """User model - Пользователи"""
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    bot_role = Column(String(50), default='start', nullable=False)  # start/broke/beginner/free/freepremium/premium
    web_role = Column(String(50), default='user', nullable=False)  # admin/manager/user
    settings_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    total_publications = Column(Integer, default=0, nullable=False)
    
    # Relationships
    objects = relationship('Object', back_populates='user', cascade='all, delete-orphan')
    telegram_accounts = relationship('TelegramAccount', back_populates='owner')
    publication_queues = relationship('PublicationQueue', back_populates='user')
    action_logs = relationship('ActionLog', back_populates='user')
    bot_web_codes = relationship('BotWebCode', back_populates='user')
    quick_access_items = relationship('QuickAccess', back_populates='user', cascade='all, delete-orphan')
    autopublish_configs = relationship('AutopublishConfig', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.telegram_id} ({self.username})>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'user_id': self.user_id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'phone': self.phone,
            'bot_role': self.bot_role,
            'web_role': self.web_role,
            'settings_json': self.settings_json or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'total_publications': self.total_publications,
        }

