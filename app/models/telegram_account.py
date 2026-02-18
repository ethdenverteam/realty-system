"""
TelegramAccount model - Telegram аккаунты пользователей
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship


class TelegramAccount(db.Model):
    """TelegramAccount model - Telegram аккаунты для публикации"""
    __tablename__ = 'telegram_accounts'
    
    account_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=False)
    session_file = Column(String(255), nullable=False)  # Path to encrypted session file
    mode = Column(String(20), default='normal', nullable=False)  # aggressive/normal/safe/smart/fix
    fix_interval_minutes = Column(Integer, nullable=True)  # Фиксированный интервал для режима 'fix' (в минутах)
    daily_limit = Column(Integer, default=200, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    owner = relationship('User', back_populates='telegram_accounts')

    # ЛЕГАСИ: прямая связь один-ко-многим через поле owner_account_id в Chat.
    # Новая каноническая связь many-to-many реализована через TelegramAccountChat.
    chats = relationship('Chat', back_populates='account')

    # Новая many-to-many привязка аккаунт ↔ чаты
    chat_links = relationship('TelegramAccountChat', back_populates='account', cascade='all, delete-orphan')
    linked_chats = relationship(
        'Chat',
        secondary='telegram_account_chats',
        back_populates='linked_accounts',
        viewonly=True,
    )

    publication_queues = relationship('PublicationQueue', back_populates='account')
    account_publication_queues = relationship('AccountPublicationQueue', back_populates='account')
    publication_history = relationship('PublicationHistory', back_populates='account')
    
    def __repr__(self):
        return f'<TelegramAccount {self.phone} (owner: {self.owner_id})>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'account_id': self.account_id,
            'owner_id': self.owner_id,
            'phone': self.phone,
            'mode': self.mode,
            'fix_interval_minutes': self.fix_interval_minutes,
            'daily_limit': self.daily_limit,
            'is_active': self.is_active,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'last_error': self.last_error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

