"""
Bot utilities - адаптированные функции из botOLD.py для работы с PostgreSQL
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import random
import string
import logging
from app.database import db
from bot.models import User, Object, Chat, BotWebCode, SystemSetting, ActionLog
from sqlalchemy import func

logger = logging.getLogger(__name__)


def get_moscow_time() -> datetime:
    """
    Получить текущее время в системном часовом поясе (МСК)
    Использует глобальную переменную SYSTEM_TIMEZONE из app.config
    """
    try:
        from app.config import SYSTEM_TIMEZONE
        from zoneinfo import ZoneInfo
        SYSTEM_TZ = ZoneInfo(SYSTEM_TIMEZONE)
    except ImportError:
        try:
            from app.config import SYSTEM_TIMEZONE
            import pytz
            SYSTEM_TZ = pytz.timezone(SYSTEM_TIMEZONE)
        except ImportError:
            # Fallback если config не доступен
            try:
                from zoneinfo import ZoneInfo
                SYSTEM_TZ = ZoneInfo('Europe/Moscow')
            except ImportError:
                import pytz
                SYSTEM_TZ = pytz.timezone('Europe/Moscow')
    
    return datetime.now(SYSTEM_TZ)


def format_moscow_datetime(dt: datetime = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Форматировать datetime в МСК в строку"""
    if dt is None:
        dt = get_moscow_time()
    return dt.strftime(format_str)


def get_user(user_id: str) -> Optional[User]:
    """Получить пользователя по Telegram ID"""
    return db.session.query(User).filter_by(telegram_id=int(user_id)).first()


def save_user(user_id: str, user_data: Dict):
    """Сохранить/обновить пользователя"""
    user = db.session.query(User).filter_by(telegram_id=int(user_id)).first()
    
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
        db.session.add(user)
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
    
    db.session.commit()
    return user


def update_user_activity(user_id: str, username: str = None):
    """Обновить активность пользователя"""
    user = db.session.query(User).filter_by(telegram_id=int(user_id)).first()
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
            db.session.add(user)
        else:
            user.last_activity = datetime.utcnow()
            if username:
                user.username = username
        
        db.session.commit()
        
        # Log user activity
        if is_new_user:
            try:
                action_log = ActionLog(
                    user_id=user.user_id,
                    action='bot_user_registered',
                    details_json={'telegram_id': int(user_id), 'username': username},
                    created_at=datetime.utcnow()
                )
                db.session.add(action_log)
                db.session.commit()
            except Exception as e:
                logger.error(f"Failed to log user registration: {e}")
                db.session.rollback()


def get_user_id_prefix(user_id: str) -> str:
    """Получить префикс ID пользователя"""
    user = get_user(user_id)
    if user and user.settings_json:
        return user.settings_json.get('id_prefix')
    return None


def set_user_id_prefix(user_id: str, prefix: str):
    """Установить префикс ID пользователя"""
    user = db.session.query(User).filter_by(telegram_id=int(user_id)).first()
    if user:
        if not user.settings_json:
            user.settings_json = {}
        user.settings_json['id_prefix'] = prefix
        db.session.commit()


def generate_next_id_prefix() -> str:
    """Сгенерировать следующий доступный префикс"""
    # Get all reserved prefixes
    users = db.session.query(User).all()
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


def get_next_object_number(user_id: str) -> int:
    """Получить следующий номер объекта"""
    user = get_user(user_id)
    if not user:
        return 1
    
    prefix = get_user_id_prefix(user_id)
    if not prefix:
        prefix = generate_next_id_prefix()
        set_user_id_prefix(user_id, prefix)
    
    # Find max number for this prefix
    objects = db.session.query(Object).filter(
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


def create_object(user_id: str) -> str:
    """Создать новый объект"""
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
    
    db.session.add(obj)
    db.session.commit()
    
    return object_id


def get_object(object_id: str) -> Optional[Object]:
    """Получить объект по ID"""
    return db.session.query(Object).filter_by(object_id=object_id).first()


def update_object(object_id: str, updates: Dict):
    """Обновить объект"""
    obj = db.session.query(Object).filter_by(object_id=object_id).first()
    if obj:
        for key, value in updates.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        obj.updated_at = datetime.utcnow()
        db.session.commit()


def get_user_objects(user_id: str) -> List[Object]:
    """Получить все объекты пользователя"""
    user = get_user(user_id)
    if not user:
        return []
    
    return db.session.query(Object).filter_by(user_id=user.user_id).all()


def get_chats() -> List[Chat]:
    """Получить все чаты"""
    return db.session.query(Chat).all()


def generate_web_code(user_id: str) -> str:
    """Сгенерировать 6-значный код для привязки к вебу"""
    user = get_user(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    # Generate unique 6-digit code
    while True:
        code = ''.join(random.choices(string.digits, k=6))
        existing = db.session.query(BotWebCode).filter_by(code=code, is_used=False).first()
        if not existing:
            break
    
    # Create code entry
    bot_code = BotWebCode(
        user_id=user.user_id,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    
    db.session.add(bot_code)
    db.session.commit()
    
    return code


def replace_digits_with_special(text: str) -> str:
    """Заменить обычные цифры на специальные символы для красивого отображения"""
    digit_map = {
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰',
        '5': '𝟱', '6': '𝟲', '7': '𝟳', '8': '𝟴', '9': '𝟵'
    }
    return ''.join(digit_map.get(char, char) for char in text)


def get_districts_config() -> Dict:
    """Получить конфигурацию районов из SystemSetting"""
    setting = db.session.query(SystemSetting).filter_by(key='districts_config').first()
    if setting and setting.value_json:
        return setting.value_json
    return {}


def get_rooms_config() -> List[str]:
    """Get rooms configuration from SystemSetting or default"""
    setting = db.session.query(SystemSetting).filter_by(key='rooms_config').first()
    if setting and setting.value_json:
        return setting.value_json
    # Default rooms
    return ["Студия", "1к", "2к", "3к", "4+к", "Дом", "евро1к", "евро2к", "евро3к"]


def get_hashtag_suffix() -> str:
    """Получить суффикс хэштегов"""
    setting = db.session.query(SystemSetting).filter_by(key='hashtag_suffix').first()
    if setting and setting.value_json:
        return setting.value_json
    return "_ф"


def get_price_ranges() -> Dict:
    """Получить ценовые диапазоны"""
    setting = db.session.query(SystemSetting).filter_by(key='price_ranges').first()
    if setting and setting.value_json:
        return setting.value_json
    return {}


def generate_district_hashtag(district_name: str, suffix: str = "_ф") -> str:
    """Генерировать хэштег для района"""
    hashtag_name = district_name.replace(" ", "")
    return f"#_{hashtag_name}{suffix}"


def generate_room_hashtag(room_type: str, suffix: str = "_ф") -> str:
    """Генерировать хэштег для типа комнат"""
    room_mapping = {
        "Студия": "студия_ст",
        "1к": "однокомнатная_1к",
        "2к": "двухкомнатная_2к",
        "3к": "трехкомнатная_3к",
        "4+к": "четырехкомнатная_4к",
        "Дом": "дом",
        "евро1к": "еврооднокомнатная_евро1к",
        "евро2к": "евродвухкомнатная_евро2к",
        "евро3к": "евротрехкомнатная_евро3к"
    }
    room_key = room_mapping.get(room_type, room_type.lower().replace(" ", ""))
    return f"#_{room_key}{suffix}"


def generate_price_range_hashtag(range_name: str, suffix: str = "_ф") -> str:
    """Генерировать хэштег для ценового диапазона"""
    range_key = range_name.replace(" ", "").replace("-", "_")
    return f"#_{range_key}{suffix}"


def _format_publication_text_compact(obj: Object, user: User = None, is_preview: bool = False) -> str:
    """
    Компактный формат публикации:
    1 строка: ЖК, Районы, Адрес
    2 строка: тип, этаж, площадь
    3 строка: ремонт
    4 строка: комментарий + перенос
    5 строка: ЦЕНА + перенос
    6 строка: контакт1
    7 строка: контакт2
    """
    lines = []
    
    # ЖК из базы данных
    residential_complex = getattr(obj, 'residential_complex', None) or ""
    
    # Районы
    districts = obj.districts_json or []
    districts_str = ", ".join(districts) if districts else ""
    
    # Адрес
    address_str = obj.address or ""
    
    # 1 строка: ЖК, Районы, Адрес
    first_line_parts = []
    if residential_complex:
        first_line_parts.append(residential_complex)
    if districts_str:
        first_line_parts.append(districts_str)
    if address_str:
        first_line_parts.append(address_str)
    
    if first_line_parts:
        lines.append(" ".join(first_line_parts))
    else:
        lines.append("")
    
    # 2 строка: тип, этаж, площадь
    second_line_parts = []
    if obj.rooms_type:
        second_line_parts.append(obj.rooms_type)
    if obj.floor:
        second_line_parts.append(f"этаж {obj.floor}")
    if obj.area:
        area_str = str(obj.area)  # Обычные символы, не заменяем
        second_line_parts.append(f"{area_str} м²")
    
    if second_line_parts:
        lines.append(" ".join(second_line_parts))
    else:
        lines.append("")
    
    # 3 строка: ремонт
    if obj.renovation:
        lines.append(obj.renovation)
    else:
        lines.append("")
    
    # 4 строка: комментарий + перенос
    if obj.comment:
        lines.append(obj.comment)
    lines.append("")  # Перенос
    
    # 5 строка: ЦЕНА + перенос
    price = obj.price or 0
    if price > 0:
        price_str = replace_digits_with_special(str(int(price)) if isinstance(price, float) else str(price))
        lines.append(f"{price_str}тр")
    lines.append("")  # Перенос
    
    # 6 строка: контакт1
    phone = obj.phone_number or (user.phone if user else None)
    contact_name = obj.contact_name or ""
    contact1_parts = []
    if contact_name:
        contact1_parts.append(contact_name)  # Обычные символы
    if phone:
        contact1_parts.append(phone)
    if contact1_parts:
        lines.append(" ".join(contact1_parts))
    
    # 7 строка: контакт2
    phone_2 = getattr(obj, 'phone_number_2', None)
    contact_name_2 = getattr(obj, 'contact_name_2', None) or ""
    show_username = getattr(obj, 'show_username', False)
    contact2_parts = []
    if contact_name_2:
        contact2_parts.append(contact_name_2)  # Обычные символы
    if phone_2:
        contact2_parts.append(phone_2)
    if show_username and user and user.username:
        contact2_parts.append(f"@{user.username}")  # Обычные символы
    if contact2_parts:
        lines.append(" ".join(contact2_parts))
    
    return "\n".join(lines)


def format_publication_text(obj: Object, user: User = None, is_preview: bool = False, publication_format: str = 'default') -> str:
    """
    Сформировать текст публикации объекта
    
    Args:
        obj: Объект недвижимости
        user: Пользователь (для контактов и футера)
        is_preview: Если True, футер не будет показан
        publication_format: 'default' - стандартный формат, 'compact' - компактный формат
    """
    # Если формат компактный, используем новый формат
    if publication_format == 'compact':
        return _format_publication_text_compact(obj, user, is_preview)
    
    # Стандартный формат (как было)
    lines = []
    
    # Цена: 🔑¦ 𝟲𝟲𝟲
    price = obj.price or 0
    if price > 0:
        price_str = replace_digits_with_special(str(int(price)) if isinstance(price, float) else str(price))
        lines.append(f"🔑¦ {price_str}")
    
    # Тип комнат: 🏠¦1к
    if obj.rooms_type:
        lines.append(f"🏠¦{obj.rooms_type}")
    
    # Районы
    districts = obj.districts_json or []
    districts_config = get_districts_config()
    
    # Собираем родительские районы
    parent_districts = set()
    second_level_districts = []
    first_level_districts = []
    
    for district in districts:
        if isinstance(district, str) and district in districts_config:
            parents = districts_config[district]
            if isinstance(parents, list) and parents:
                parent_districts.update(parents)
                second_level_districts.append(district)
            else:
                first_level_districts.append(district)
        else:
            first_level_districts.append(district)
    
    # Районы первого уровня
    if len(first_level_districts) == 1:
        lines.append(f"🗺¦{first_level_districts[0]}")
    elif len(first_level_districts) > 1:
        lines.append(f"🗺¦{', '.join(first_level_districts)}")
    
    # Площадь
    if obj.area:
        area_str = str(obj.area)  # Обычные символы, не заменяем
        lines.append(f"𝙈 ²¦{area_str}")
    
    # Этаж
    if obj.floor:
        floor_str = str(obj.floor)  # Обычные символы, не заменяем
        lines.append(f"📐¦{floor_str}")
    
    # Ремонт
    if obj.renovation:
        lines.append(f"🛋¦{obj.renovation}")
    
    # ЖК из базы данных
    residential_complex = getattr(obj, 'residential_complex', None) or ""
    if residential_complex:
        lines.append(f"🏘¦{residential_complex}")
    
    # Адрес
    if obj.address:
        lines.append(f"📍¦{obj.address}")
    
    # Родительские районы
    if parent_districts:
        parent_list = list(parent_districts)
        if len(parent_list) == 1:
            lines.append(f"🗾¦{parent_list[0]}")
        else:
            lines.append(f"🗾¦{', '.join(parent_list)}")
    
    # Пустая строка перед комментарием
    lines.append("")
    
    # Комментарий
    if obj.comment:
        lines.append(f"📝¦")
        lines.append(obj.comment)
    
    # Футер (только если не превью)
    if user and not is_preview:
        show_footer = False
        if user.settings_json:
            show_footer = user.settings_json.get('show_footer', False)
        
        if show_footer:
            lines.append("")
            lines.append("🔑¦<a href=\"http://t.me/keyskrd\">Ключи</a>")
            lines.append("🏢¦<a href=\"http://t.me/MasterKeyRobot\">@MasterKeyRobot</a>")
            lines.append("🗂¦<a href=\"https://t.me/addlist/QDGm9RwOldE4YzM6\">Папка со всеми чатами</a>")
            lines.append("")
    
    # Хэштеги
    hashtags = []
    suffix = get_hashtag_suffix()
    
    if obj.rooms_type:
        hashtags.append(generate_room_hashtag(obj.rooms_type, suffix))
    
    for district in districts:
        if isinstance(district, str):
            hashtags.append(generate_district_hashtag(district, suffix))
    
    price_ranges = get_price_ranges()
    if price > 0 and price_ranges:
        for range_name, range_values in price_ranges.items():
            if isinstance(range_values, list) and len(range_values) >= 2:
                if range_values[0] <= price < range_values[1]:
                    hashtags.append(generate_price_range_hashtag(range_name, suffix))
                    break
    
    if hashtags:
        lines.append(" ".join(hashtags))
        lines.append("")
    
    # Контакты
    phone = obj.phone_number or (user.phone if user else None)
    contact_name = obj.contact_name or ""
    phone_2 = getattr(obj, 'phone_number_2', None)
    contact_name_2 = getattr(obj, 'contact_name_2', None) or ""
    show_username = obj.show_username or False
    
    if contact_name or phone or contact_name_2 or phone_2 or (show_username and user and user.username):
        if not hashtags:
            lines.append("")
        if contact_name:
            lines.append(f"🕴🏻¦{contact_name}")  # Обычные символы, не заменяем
        if phone:
            lines.append(f"☎️¦{phone}")
        if contact_name_2:
            lines.append(f"🕴🏻¦{contact_name_2}")  # Обычные символы, не заменяем
        if phone_2:
            lines.append(f"☎️¦{phone_2}")
        if show_username and user and user.username:
            lines.append(f"📩¦@{user.username}")  # Обычные символы, не заменяем
    
    # Показываем родительские районы в конце
    if parent_districts:
        parent_list = list(parent_districts)
        if len(parent_list) == 1:
            lines.append(f"🗺¦ {parent_list[0]}")
        else:
            lines.append(f"🗺¦ {', '.join(parent_list)}")
    
    # Районы второго уровня
    if len(second_level_districts) > 1:
        lines.append(f"🗾¦ {', '.join(second_level_districts)}")
    
    return "\n".join(lines)