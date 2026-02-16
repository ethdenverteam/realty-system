"""
ChatGroup model - Группы чатов для удобного выбора
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship


class ChatGroup(db.Model):
    """ChatGroup model - Группы чатов для удобного выбора"""
    __tablename__ = 'chat_groups'
    
    group_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    # Массив chat_id из таблицы chats
    chat_ids = Column(JSON, nullable=False)  # [1, 2, 3, ...]
    # Исходные ссылки на чаты (для подписки)
    chat_links = Column(JSON, nullable=True)  # ["https://t.me/+...", ...]
    # Назначение группы: 'subscription' (для подписки на чаты) или 'autopublish' (для автопубликации)
    purpose = Column(String(50), nullable=False, default='autopublish', index=True)  # 'subscription' | 'autopublish'
    # Категория связи (как в админских чатах)
    category = Column(String(100), nullable=True)  # rooms_1k/rooms_2k/district_center/price_4000_6000 (legacy)
    filters_json = Column(JSON, nullable=True)  # Extended filters: {rooms_types: [], districts: [], price_min: 0, price_max: 0}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship('User', back_populates='chat_groups')
    
    def __repr__(self):
        return f'<ChatGroup {self.group_id} ({self.name})>'
    
    def to_dict(self):
        """Convert to dictionary"""
        result = {
            'group_id': self.group_id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'chat_ids': self.chat_ids or [],
            'chat_links': self.chat_links or [],
            'purpose': getattr(self, 'purpose', 'autopublish'),  # Default для старых записей
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        # Safely handle category and filters_json - they might not exist in the database
        try:
            result['category'] = self.category
        except AttributeError:
            result['category'] = None
        try:
            result['filters_json'] = self.filters_json or {}
        except AttributeError:
            result['filters_json'] = {}
        return result

