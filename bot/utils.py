"""
Bot utilities - адаптированные функции из botOLD.py для работы с PostgreSQL
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import random
import string
import logging
from bot.database import get_db
from bot.models import User, Object, Chat, BotWebCode, SystemSetting, ActionLog
from sqlalchemy import func

logger = logging.getLogger(__name__)


def get_moscow_time() -> datetime:
    """Получить текущее время в московском часовом поясе"""
    try:
        from zoneinfo import ZoneInfo
        MOSCOW_TZ = ZoneInfo('Europe/Moscow')
    except ImportError:
        import pytz
        MOSCOW_TZ = pytz.timezone('Europe/Moscow')
    
    return datetime.now(MOSCOW_TZ)


def format_moscow_datetime(dt: datetime = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Форматировать datetime в МСК в строку"""
    if dt is None:
        dt = get_moscow_time()
    return dt.strftime(format_str)


def get_user(user_id: str) -> Optional[User]:
    """Получить пользователя по Telegram ID"""
    db = get_db()
    try:
        user = db.query(User).filter_by(telegram_id=int(user_id)).first()
        return user
    finally:
        db.close()


def save_user(user_id: str, user_data: Dict):
    """Сохранить/обновить пользователя"""
    db = get_db()
    try:
        user = db.query(User).filter_by(telegram_id=int(user_id)).first()
        
        if not user:
            user = User(
                telegram_id=int(user_id),
                username=user_data.get('username', ''),
                phone=user_data.get('phone_number', ''),
                bot_role=user_data.get('role', 'start'),
                settings_json=user_data.get('settings_json', {}),
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )
            db.add(user)
        else:
            if 'username' in user_data:
                user.username = user_data['username']
            if 'phone_number' in user_data:
                user.phone = user_data['phone_number']
            if 'role' in user_data:
                user.bot_role = user_data['role']
            if 'settings_json' in user_data:
                user.settings_json = user_data.get('settings_json', {})
            user.last_activity = datetime.utcnow()
        
        db.commit()
        return user
    finally:
        db.close()


def update_user_activity(user_id: str, username: str = None):
    """Обновить активность пользователя"""
    db = get_db()
    try:
        user = db.query(User).filter_by(telegram_id=int(user_id)).first()
        is_new_user = False
        
        if not user:
            is_new_user = True
            user = User(
                telegram_id=int(user_id),
                username=username or "",
                bot_role='start',
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )
            db.add(user)
        else:
            user.last_activity = datetime.utcnow()
            if username:
                user.username = username
        
        db.commit()
        
        # Log user activity
        if is_new_user:
            try:
                action_log = ActionLog(
                    user_id=user.user_id,
                    action='bot_user_registered',
                    details_json={'telegram_id': int(user_id), 'username': username},
                    created_at=datetime.utcnow()
                )
                db.add(action_log)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to log user registration: {e}")
                db.rollback()
    finally:
        db.close()


def get_user_id_prefix(user_id: str) -> str:
    """Получить префикс ID пользователя"""
    user = get_user(user_id)
    if user and user.settings_json:
        return user.settings_json.get('id_prefix')
    return None


def set_user_id_prefix(user_id: str, prefix: str):
    """Установить префикс ID пользователя"""
    db = get_db()
    try:
        user = db.query(User).filter_by(telegram_id=int(user_id)).first()
        if user:
            if not user.settings_json:
                user.settings_json = {}
            user.settings_json['id_prefix'] = prefix
            db.commit()
    finally:
        db.close()


def generate_next_id_prefix() -> str:
    """Сгенерировать следующий доступный префикс"""
    db = get_db()
    try:
        # Get all reserved prefixes
        users = db.query(User).all()
        reserved = []
        for u in users:
            if u.settings_json and 'id_prefix' in u.settings_json:
                reserved.append(u.settings_json['id_prefix'])
        
        # Generate new prefix
        for first in range(ord('А'), ord('Я') + 1):
            for second in range(ord('А'), ord('Я') + 1):
                for third in range(ord('А'), ord('Я') + 1):
                    prefix = chr(first) + chr(second) + chr(third)
                    if prefix not in reserved:
                        return prefix
        
        return "ААА"
    finally:
        db.close()


def get_next_object_number(user_id: str) -> int:
    """Получить следующий номер объекта"""
    db = get_db()
    try:
        user = get_user(user_id)
        if not user:
            return 1
        
        prefix = get_user_id_prefix(user_id)
        if not prefix:
            prefix = generate_next_id_prefix()
            set_user_id_prefix(user_id, prefix)
        
        # Find max number for this prefix
        objects = db.query(Object).filter(
            Object.object_id.like(f'{prefix}%')
        ).all()
        
        max_num = 0
        for obj in objects:
            try:
                num = int(obj.object_id[len(prefix):])
                if num > max_num:
                    max_num = num
            except:
                pass
        
        return max_num + 1
    finally:
        db.close()


def create_object(user_id: str) -> str:
    """Создать новый объект"""
    db = get_db()
    try:
        user = get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        prefix = get_user_id_prefix(user_id)
        if not prefix:
            prefix = generate_next_id_prefix()
            set_user_id_prefix(user_id, prefix)
        
        obj_number = get_next_object_number(user_id)
        object_id = f"{prefix}{obj_number:03d}"
        
        default_show_username = False
        if user.settings_json:
            default_show_username = user.settings_json.get('default_show_username', False)
        
        obj = Object(
            object_id=object_id,
            user_id=user.user_id,
            rooms_type="",
            price=0,
            districts_json=[],
            photos_json=[],
            contact_name=user.settings_json.get('contact_name', '') if user.settings_json else '',
            show_username=default_show_username,
            status='черновик',
            source='bot',
            creation_date=datetime.utcnow()
        )
        
        db.add(obj)
        db.commit()
        
        return object_id
    finally:
        db.close()


def get_object(object_id: str) -> Optional[Object]:
    """Получить объект по ID"""
    db = get_db()
    try:
        return db.query(Object).filter_by(object_id=object_id).first()
    finally:
        db.close()


def update_object(object_id: str, updates: Dict):
    """Обновить объект"""
    db = get_db()
    try:
        obj = db.query(Object).filter_by(object_id=object_id).first()
        if obj:
            for key, value in updates.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            obj.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def get_user_objects(user_id: str) -> List[Object]:
    """Получить все объекты пользователя"""
    db_session = get_db()
    try:
        user = get_user(user_id)
        if not user:
            return []
        
        return db_session.query(Object).filter_by(user_id=user.user_id).all()
    finally:
        db_session.close()


def get_chats() -> List[Chat]:
    """Получить все чаты"""
    db = get_db()
    try:
        return db.query(Chat).all()
    finally:
        db.close()


def generate_web_code(user_id: str) -> str:
    """Сгенерировать 6-значный код для привязки к вебу"""
    db = get_db()
    try:
        user = get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Generate unique 6-digit code
        while True:
            code = ''.join(random.choices(string.digits, k=6))
            existing = db.query(BotWebCode).filter_by(code=code, is_used=False).first()
            if not existing:
                break
        
        # Create code entry
        bot_code = BotWebCode(
            user_id=user.user_id,
            code=code,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        
        db.add(bot_code)
        db.commit()
        
        return code
    finally:
        db.close()

