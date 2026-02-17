"""
ChatGroup model - Группы чатов для удобного выбора
"""
from app.database import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean
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
    # Структура: [{"link": "https://t.me/+...", "telegram_chat_id": "-1001234567890", "title": "Название чата"}, ...]
    # telegram_chat_id и title могут быть null до успешной подписки
    chat_links = Column(JSON, nullable=True)  # [{"link": str, "telegram_chat_id": str|null, "title": str|null}, ...]
    # Назначение группы: 'subscription' (для подписки на чаты) или 'autopublish' (для автопубликации)
    purpose = Column(String(50), nullable=False, default='autopublish', index=True)  # 'subscription' | 'autopublish'
    # Публичный список (виден всем пользователям на странице подписок)
    is_public = Column(Boolean, nullable=False, default=False, index=True)
    # Категория связи (как в админских чатах)
    category = Column(String(100), nullable=True)  # rooms_1k/rooms_2k/district_center/price_4000_6000 (legacy)
    filters_json = Column(JSON, nullable=True)  # Extended filters: {rooms_types: [], districts: [], price_min: 0, price_max: 0}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship('User', back_populates='chat_groups')
    
    def __repr__(self):
        return f'<ChatGroup {self.group_id} ({self.name})>'
    
    def get_chat_links_list(self):
        """
        Получить список ссылок в новом формате (массив объектов).
        Если данные в старом формате (массив строк) - конвертирует автоматически.
        """
        links_data = self.chat_links or []
        if not links_data:
            return []
        
        # Если первый элемент - строка, значит старый формат - конвертируем
        if links_data and isinstance(links_data[0], str):
            return [{"link": link, "telegram_chat_id": None, "title": None} for link in links_data]
        
        # Уже новый формат
        return links_data
    
    def set_chat_links_list(self, links_list):
        """
        Установить список ссылок в новом формате.
        links_list: [{"link": str, "telegram_chat_id": str|null, "title": str|null}, ...]
        """
        self.chat_links = links_list
    
    def update_chat_link_info(self, link: str, telegram_chat_id: str = None, title: str = None):
        """
        Обновить информацию о чате (telegram_chat_id и title) для конкретной ссылки.
        Если чат с такой ссылкой не найден - добавляет новый.
        """
        links_list = self.get_chat_links_list()
        
        # Ищем существующую запись по ссылке
        found = False
        for item in links_list:
            if item.get('link') == link:
                if telegram_chat_id is not None:
                    item['telegram_chat_id'] = telegram_chat_id
                if title is not None:
                    item['title'] = title
                found = True
                break
        
        # Если не нашли - добавляем новую запись
        if not found:
            links_list.append({
                "link": link,
                "telegram_chat_id": telegram_chat_id,
                "title": title,
            })
        
        self.chat_links = links_list
    
    def get_link_by_index(self, index: int) -> str:
        """
        Получить ссылку по индексу (для обратной совместимости с задачами подписки).
        """
        links_list = self.get_chat_links_list()
        if 0 <= index < len(links_list):
            return links_list[index].get('link', '')
        return ''
    
    def to_dict(self):
        """Convert to dictionary"""
        result = {
            'group_id': self.group_id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'chat_ids': self.chat_ids or [],
            'chat_links': self.get_chat_links_list(),  # Используем новый формат
            'purpose': getattr(self, 'purpose', 'autopublish'),  # Default для старых записей
            'is_public': getattr(self, 'is_public', False),
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

