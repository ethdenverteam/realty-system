"""
AutopublishConfig model - Настройки автопубликации объектов
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship


class AutopublishConfig(db.Model):
    """AutopublishConfig model - Настройки автопубликации объектов"""
    __tablename__ = 'autopublish_configs'

    config_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    object_id = Column(String(50), ForeignKey('objects.object_id'), nullable=False, index=True)

    # Основные флаги
    enabled = Column(Boolean, default=True, nullable=False)
    bot_enabled = Column(Boolean, default=True, nullable=False)  # Автопубликация через бота

    # Расширенные настройки для аккаунтов пользователей
    # Формат:
    # {
    #   "accounts": [
    #       {
    #           "account_id": 1,
    #           "chat_ids": [10, 11, 12]
    #       }
    #   ]
    # }
    accounts_config_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship('User', back_populates='autopublish_configs')
    object = relationship('Object', back_populates='autopublish_config')

    def __repr__(self):
        return f'<AutopublishConfig {self.config_id} (user: {self.user_id}, object: {self.object_id}, enabled: {self.enabled})>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'config_id': self.config_id,
            'user_id': self.user_id,
            'object_id': self.object_id,
            'enabled': self.enabled,
            'bot_enabled': self.bot_enabled,
            'accounts_config_json': self.accounts_config_json or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


