"""
Statistics model - Статистика системы
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON


class Statistics(db.Model):
    """Statistics model - Статистика системы"""
    __tablename__ = 'statistics'
    
    stat_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    dimensions_json = Column(JSON, nullable=True)  # Additional dimensions
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Statistics {self.metric_name} = {self.metric_value}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'stat_id': self.stat_id,
            'date': self.date.isoformat() if self.date else None,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'dimensions_json': self.dimensions_json or {},
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None,
        }

