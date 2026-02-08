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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship('User', back_populates='chat_groups')
    
    def __repr__(self):
        return f'<ChatGroup {self.group_id} ({self.name})>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'group_id': self.group_id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'chat_ids': self.chat_ids or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

