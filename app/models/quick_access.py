"""
QuickAccess model - Быстрый доступ к объектам (ВЫБОР)
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship


class QuickAccess(db.Model):
    """QuickAccess model - Быстрый доступ к объектам"""
    __tablename__ = 'quick_access'
    
    quick_access_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    object_id = Column(String(50), ForeignKey('objects.object_id'), nullable=False, index=True)
    display_order = Column(Integer, nullable=False, default=0)  # Порядок отображения
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship('User', back_populates='quick_access_items')
    object = relationship('Object')
    
    def __repr__(self):
        return f'<QuickAccess {self.quick_access_id} (user: {self.user_id}, object: {self.object_id})>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'quick_access_id': self.quick_access_id,
            'user_id': self.user_id,
            'object_id': self.object_id,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
