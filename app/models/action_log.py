"""
ActionLog model - Логи действий
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship


class ActionLog(db.Model):
    """ActionLog model - Логи действий пользователей"""
    __tablename__ = 'action_logs'
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    details_json = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship('User', back_populates='action_logs')
    
    def __repr__(self):
        return f'<ActionLog {self.log_id} ({self.action})>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'log_id': self.log_id,
            'user_id': self.user_id,
            'action': self.action,
            'details_json': self.details_json or {},
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

