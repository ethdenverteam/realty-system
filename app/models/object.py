"""
Object model - Объекты недвижимости
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship


class Object(db.Model):
    """Object model - Объекты недвижимости"""
    __tablename__ = 'objects'
    
    object_id = Column(String(50), primary_key=True)  # Format: ПРЕФИКС001
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    rooms_type = Column(String(50), nullable=False)  # Студия/1к/2к/3к/4+к/Дом/евро1к/евро2к/евро3к
    price = Column(Float, nullable=False)  # Price in thousands of rubles
    districts_json = Column(JSON, nullable=False)  # List of districts
    region = Column(String(100), nullable=True)  # Parent region
    city = Column(String(100), nullable=True)  # Parent city
    photos_json = Column(JSON, default=list)  # List with single photo (path or file_id dict)
    area = Column(Float, nullable=True)  # Area in m²
    floor = Column(String(20), nullable=True)  # Floor like "6/9"
    address = Column(String(255), nullable=True)
    residential_complex = Column(String(255), nullable=True)  # ЖК (жилой комплекс)
    renovation = Column(String(50), nullable=True)  # Renovation state
    comment = Column(Text, nullable=True)
    contact_name = Column(String(100), nullable=True)
    show_username = Column(Boolean, default=False, nullable=False)
    phone_number = Column(String(20), nullable=True)
    contact_name_2 = Column(String(100), nullable=True)
    phone_number_2 = Column(String(20), nullable=True)
    status = Column(String(50), default='черновик', nullable=False)  # черновик/опубликовано/запланировано/архив
    source = Column(String(10), default='bot', nullable=False)  # bot/web
    publication_date = Column(DateTime, nullable=True)
    creation_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship('User', back_populates='objects')
    publication_queues = relationship('PublicationQueue', back_populates='object')
    account_publication_queues = relationship('AccountPublicationQueue', back_populates='object')
    publication_history = relationship('PublicationHistory', back_populates='object')
    autopublish_config = relationship('AutopublishConfig', back_populates='object', uselist=False)
    
    def __repr__(self):
        return f'<Object {self.object_id} ({self.rooms_type}, {self.price}к)>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'object_id': self.object_id,
            'user_id': self.user_id,
            'rooms_type': self.rooms_type,
            'price': self.price,
            'districts_json': self.districts_json or [],
            'region': self.region,
            'city': self.city,
            'photos_json': self.photos_json or [],
            'area': self.area,
            'floor': self.floor,
            'address': self.address,
            'residential_complex': self.residential_complex,
            'renovation': self.renovation,
            'comment': self.comment,
            'contact_name': self.contact_name,
            'show_username': self.show_username,
            'phone_number': self.phone_number,
            'contact_name_2': self.contact_name_2,
            'phone_number_2': self.phone_number_2,
            'status': self.status,
            'source': self.source,
            'publication_date': self.publication_date.isoformat() if self.publication_date else None,
            'creation_date': self.creation_date.isoformat() if self.creation_date else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

