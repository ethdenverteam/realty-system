"""
SystemSetting model - Системные настройки
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON


class SystemSetting(db.Model):
    """SystemSetting model - Системные настройки"""
    __tablename__ = 'system_settings'
    
    setting_id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value_json = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(Integer, nullable=True)  # User ID who updated
    
    def __repr__(self):
        return f'<SystemSetting {self.key}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'setting_id': self.setting_id,
            'key': self.key,
            'value_json': self.value_json or {},
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
        }

