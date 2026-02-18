"""
TelegramAccountChat model - Связь many-to-many между TelegramAccount и Chat
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship


class TelegramAccountChat(db.Model):
    """
    TelegramAccountChat - связывает один Telegram аккаунт пользователя с одним чатом.
    Один чат может быть привязан к нескольким аккаунтам, и один аккаунт к множеству чатов.
    """
    __tablename__ = 'telegram_account_chats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('telegram_accounts.account_id'), nullable=False, index=True)
    chat_id = Column(Integer, ForeignKey('chats.chat_id'), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('account_id', 'chat_id', name='uq_telegram_account_chat_account_chat'),
    )

    # Relationships
    account = relationship('TelegramAccount', back_populates='chat_links')
    chat = relationship('Chat', back_populates='account_links')


