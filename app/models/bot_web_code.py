"""
BotWebCode model - Коды привязки бота к вебу
"""
from app.database import db
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship


class BotWebCode(db.Model):
    """BotWebCode model - Коды для привязки Telegram бота к веб-интерфейсу"""
    __tablename__ = 'bot_web_codes'
    
    code_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    code = Column(String(6), unique=True, nullable=False, index=True)
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship('User', back_populates='bot_web_codes')
    
    def __repr__(self):
        return f'<BotWebCode {self.code} (user: {self.user_id})>'
    
    def is_valid(self):
        """Check if code is valid (not used and not expired)"""
        return not self.is_used and datetime.utcnow() < self.expires_at
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'code_id': self.code_id,
            'user_id': self.user_id,
            'code': self.code,
            'is_used': self.is_used,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

