"""
Telegram бот для публикации объектов недвижимости
Все в одном файле для удобства
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Для Python < 3.9 используем pytz
    try:
        import pytz
        ZoneInfo = lambda tz: pytz.timezone(tz)
    except ImportError:
        raise ImportError("Необходим либо zoneinfo (Python 3.9+), либо pytz")
from typing import Dict, List, Any, Optional
import re
import json
import aiofiles
import logging
import traceback
import sys

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
from telegram.constants import ParseMode

# ==================== КОНСТАНТЫ И НАСТРОЙКИ ====================
API_TOKEN = "8260262810:AAHbbqKr64RWyQrXagIgcU-c2t3fxSAcWXk"
ADMIN_ID = 7615679936
CHANNEL_ID = -1001981637818
AUTHORS_CHAT_ID = -1001821062207
CHECK_SUBSCRIPTION_ENABLED = True

# Лимиты Telegram
TELEGRAM_MESSAGES_PER_MINUTE = 20
TELEGRAM_MESSAGE_INTERVAL = 60 / TELEGRAM_MESSAGES_PER_MINUTE  # 3 секунды между сообщениями

# Роли пользователей
ROLE_START = "start"
ROLE_BROKE = "broke"
ROLE_BEGINNER = "beginner"
ROLE_FREE = "free"
ROLE_FREEPREMIUM = "freepremium"
ROLE_PREMIUM = "premium"
ROLE_PROTIME = "protime"

# Временные слоты для публикаций
SLOT_CATEGORY_8_9 = "8-9"  # Для определенных категорий
SLOT_DEFAULT_9_12 = "9-12"  # По умолчанию (общая очередь)
SLOT_CUSTOM_12_22 = "12-22"  # Слоты с 12 до 22 с интервалом 15 минут

# ==================== ФУНКЦИИ РАБОТЫ С ВРЕМЕНЕМ (МСК) ====================
# Устанавливаем московский часовой пояс один раз
MOSCOW_TZ = ZoneInfo('Europe/Moscow')

def get_moscow_time() -> datetime:
    """Получить текущее время в московском часовом поясе"""
    return datetime.now(MOSCOW_TZ)

def get_moscow_time_utc() -> datetime:
    """Получить текущее время UTC, затем конвертировать в МСК"""
    now_utc = datetime.now(timezone.utc)
    return now_utc.astimezone(MOSCOW_TZ)

def format_moscow_datetime(dt: datetime = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Форматировать datetime в МСК в строку"""
    if dt is None:
        dt = get_moscow_time()
    elif dt.tzinfo is None:
        # Если время без timezone, считаем что это МСК
        dt = dt.replace(tzinfo=MOSCOW_TZ)
    elif dt.tzinfo != MOSCOW_TZ:
        # Конвертируем в МСК если другой timezone
        dt = dt.astimezone(MOSCOW_TZ)
    return dt.strftime(format_str)

def parse_moscow_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """Парсить строку даты как время МСК"""
    dt = datetime.strptime(date_str, format_str)
    return dt.replace(tzinfo=MOSCOW_TZ)

# ==================== ТЕКСТЫ СООБЩЕНИЙ ====================
ADMIN_PANEL_TEXT = "Панель администратора"
WELCOME_TEXT = "Добро пожаловать! Выберите действие:"
SUBSCRIPTION_REQUIRED = "Для использования бота необходимо подписаться на канал и чат."
MAIN_MENU_TEXT = "Главное меню"
ADD_OBJECT_ROOMS_QUESTION = "Сколько комнат?"
ADD_OBJECT_DISTRICT_QUESTION = "Выберите район"
ADD_OBJECT_ANOTHER_DISTRICT = "Надо ли добавить еще район?"
ADD_OBJECT_PRICE_QUESTION = "Укажите сумму в тысячах рублей"
ADD_OBJECT_MEDIA_QUESTION = "Отправьте медиа (фото/видео). Можно отправить до 10 файлов."
ADD_OBJECT_CAPTION_QUESTION = "Добавьте подпись (любой текст)"
OBJECT_PREVIEW_TITLE = "Предпросмотр объекта:"
OBJECT_PREVIEW_ROOMS = "Тип комнат"
OBJECT_PREVIEW_PRICE = "Цена"
OBJECT_PREVIEW_DISTRICTS = "Районы"
OBJECT_PREVIEW_CAPTION = "Описание"
OBJECT_PREVIEW_PHONE = "Телефон"
PUBLICATION_SUCCESS = "Объект успешно опубликован в {count} чат(ов)!"
PUBLICATION_FAILED = "Ошибка при публикации объекта."
MY_OBJECTS_TITLE = "Мои объекты"
NO_OBJECTS = "У вас пока нет объектов."
OBJECT_INFO = "Информация об объекте:"
OBJECT_STATUS_DRAFT = "Черновик"
OBJECT_STATUS_PUBLISHED = "Опубликовано"
SETTINGS_TITLE = "Настройки"
SETTINGS_PHONE_ADD = "Введите номер телефона:\n\nНомер в формате:\n89693386969"
SETTINGS_PHONE_CHANGE = "Введите новый номер телефона:\n\nНомер в формате:\n89693386969"
SETTINGS_PHONE_SAVED = "Номер телефона сохранен."
SETTINGS_PROFILE_INFO = "Информация о профиле:"
ADMIN_ADD_CHAT_ID = "Введите chat_id чата (можно через @username или числовой ID):"
ADMIN_ADD_CHAT_TITLE = "Введите название чата:"
ADMIN_ADD_CHAT_TYPE = "Выберите тип чата:"
ADMIN_ADD_CHAT_PARAMS = "Выберите параметры чата:"
ADMIN_CHAT_ADDED = "Чат успешно добавлен!"
ADMIN_CHAT_LIST = "Список чатов:"
STATISTICS_TITLE = "Статистика"
STATISTICS_USERS_TOTAL = "Всего пользователей"
STATISTICS_USERS_ACTIVE = "Активных пользователей"
STATISTICS_USERS_NEW = "Новых пользователей"
STATISTICS_PUBLICATIONS_TOTAL = "Всего публикаций"
STATISTICS_PUBLICATIONS_PERIOD = "Публикаций за период"
STATISTICS_PUBLICATIONS_BY_CHAT = "Публикации по чатам"
STATISTICS_SCHEDULED = "Запланировано"
ERROR_INVALID_PRICE = "Ошибка: введите положительное число."
ERROR_INVALID_INPUT = "Ошибка: неверный ввод."
ERROR_ACCESS_DENIED = "Ошибка: доступ запрещен."
ERROR_FILE_NOT_FOUND = "Ошибка: файл не найден."
BUTTON_YES = "ДА"
BUTTON_NO = "НЕТ"
BUTTON_PUBLISH = "Опубликовать"
BUTTON_EDIT = "Редактировать"
BUTTON_CANCEL = "Отменить"
BUTTON_VIEW = "Просмотреть"
BUTTON_DELETE = "Удалить"
BUTTON_BACK = "Назад"
BUTTON_SUBSCRIBE = "Подписаться"
BUTTON_CHECK_SUBSCRIPTION = "Проверить подписку"

# ==================== ФУНКЦИИ РАБОТЫ С ДАННЫМИ ====================
async def ensure_file_exists(file_path: str, default_content: Any = None):
    """Создает файл, если он не существует"""
    if not os.path.exists(file_path):
        if default_content is None:
            default_content = {}
        await save_json(file_path, default_content)

async def load_json(file_path: str) -> Dict:
    """Асинхронная загрузка JSON файла"""
    try:
        await ensure_file_exists(file_path, {})
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            if not content.strip():
                return {}
            return json.loads(content)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}

async def save_json(file_path: str, data: Dict):
    """Асинхронное сохранение JSON файла"""
    try:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error saving {file_path}: {e}")

async def get_user(user_id: str) -> Optional[Dict]:
    """Получить информацию о пользователе"""
    users = await load_json("users.json")
    return users.get(str(user_id))

async def save_user(user_id: str, user_data: Dict):
    """Сохранить/обновить информацию о пользователе"""
    users = await load_json("users.json")
    users[str(user_id)] = user_data
    await save_json("users.json", users)

async def update_user_activity(user_id: str, username: str = None):
    """Обновить активность пользователя"""
    user = await get_user(str(user_id))
    now = format_moscow_datetime()
    
    if not user:
        user = {
            "username": username or "",
            "phone_number": "",
            "first_seen": now,
            "last_activity": now,
            "subscription_checked": False,
            "total_publications": 0,
            "role": ROLE_START,
            "active_periods": {
                "day": [],
                "week": [],
                "month": []
            }
        }
    else:
        user["last_activity"] = now
        if username:
            user["username"] = username
        # Если роль не установлена, устанавливаем start
        if "role" not in user:
            user["role"] = ROLE_START
    
    today = format_moscow_datetime(format_str="%Y-%m-%d")
    if today not in user["active_periods"]["day"]:
        user["active_periods"]["day"].append(today)
    if today not in user["active_periods"]["week"]:
        user["active_periods"]["week"].append(today)
    if today not in user["active_periods"]["month"]:
        user["active_periods"]["month"].append(today)
    
    await save_user(str(user_id), user)

async def get_user_id_prefix(user_id: str) -> str:
    """Получить трехбуквенный префикс ID для пользователя"""
    user_info = await get_user(str(user_id))
    if user_info and "id_prefix" in user_info:
        return user_info["id_prefix"]
    return None

async def set_user_id_prefix(user_id: str, prefix: str):
    """Установить трехбуквенный префикс ID для пользователя"""
    user_info = await get_user(str(user_id))
    if not user_info:
        user_info = {}
    user_info["id_prefix"] = prefix
    await save_user(str(user_id), user_info)

async def get_reserved_prefixes() -> List[str]:
    """Получить список зарезервированных префиксов"""
    users = await load_json("users.json")
    reserved = []
    for user_data in users.values():
        if "id_prefix" in user_data:
            reserved.append(user_data["id_prefix"])
    return reserved

async def generate_next_id_prefix() -> str:
    """Сгенерировать следующий доступный трехбуквенный префикс"""
    reserved = await get_reserved_prefixes()
    
    # Генерируем все возможные комбинации из трех букв (А-Я)
    for first in range(ord('А'), ord('Я') + 1):
        for second in range(ord('А'), ord('Я') + 1):
            for third in range(ord('А'), ord('Я') + 1):
                prefix = chr(first) + chr(second) + chr(third)
                if prefix not in reserved:
                    return prefix
    
    # Если все комбинации заняты, используем расширенный диапазон
    for first in range(ord('А'), ord('Я') + 1):
        for second in range(ord('А'), ord('Я') + 1):
            for third in range(ord('А'), ord('Я') + 1):
                prefix = chr(first) + chr(second) + chr(third)
                if prefix not in reserved:
                    return prefix
    
    return "ААА"  # Fallback

async def get_next_object_number(user_id: str) -> int:
    """Получить следующий номер объекта для пользователя"""
    objects = await load_json("objects.json")
    prefix = await get_user_id_prefix(user_id)
    if not prefix:
        prefix = await generate_next_id_prefix()
        await set_user_id_prefix(user_id, prefix)
    
    max_num = 0
    for obj_id, obj_data in objects.items():
        if obj_data.get("user_id") == str(user_id):
            # Проверяем, соответствует ли ID формату префикса + число
            if obj_id.startswith(prefix):
                try:
                    num_part = obj_id[len(prefix):]
                    num = int(num_part)
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
    
    return max_num + 1

async def create_object(user_id: str) -> str:
    """Создать новый объект и вернуть его ID"""
    objects = await load_json("objects.json")
    
    # Получаем или создаем префикс для пользователя
    prefix = await get_user_id_prefix(user_id)
    if not prefix:
        prefix = await generate_next_id_prefix()
        await set_user_id_prefix(user_id, prefix)
    
    # Получаем следующий номер объекта
    obj_number = await get_next_object_number(user_id)
    object_id = f"{prefix}{obj_number}"
    
    # Получаем настройки пользователя для применения default_show_username
    user_info = await get_user(str(user_id))
    default_show_username = user_info.get("default_show_username", False) if user_info else False
    
    objects[object_id] = {
        "user_id": str(user_id),
        "rooms_type": "",
        "districts": [],
        "price": 0,
        "media_files": [],
        "caption": "",
        "phone_number": "",
        "contact_name": user_info.get("contact_name", "") if user_info else "",
        "show_username": default_show_username,
        "area": "",
        "floor": "",
        "comment": "",
        "renovation": "",
        "address": "",
        "creation_date": format_moscow_datetime(),
        "status": "черновик",
        "publication_date": "",
        "target_chats": [],
        "scheduled_time": None,
        "scheduled_slot": None,
        "publication_type": None  # "immediate", "scheduled"
    }
    
    await save_json("objects.json", objects)
    return object_id

async def get_object(object_id: str) -> Optional[Dict]:
    """Получить объект по ID"""
    objects = await load_json("objects.json")
    return objects.get(object_id)

async def update_object(object_id: str, updates: Dict):
    """Обновить объект"""
    objects = await load_json("objects.json")
    if object_id in objects:
        objects[object_id].update(updates)
        await save_json("objects.json", objects)

async def get_user_objects(user_id: str) -> List[Dict]:
    """Получить все объекты пользователя"""
    objects = await load_json("objects.json")
    return [
        {"id": obj_id, **obj_data}
        for obj_id, obj_data in objects.items()
        if obj_data.get("user_id") == str(user_id)
    ]

async def get_user_sort_order(user_id: str) -> str:
    """Получить порядок сортировки объектов пользователя (new или old)"""
    user_info = await get_user(str(user_id))
    if user_info and "sort_order" in user_info:
        return user_info["sort_order"]
    return "new"  # По умолчанию новые сначала

async def set_user_sort_order(user_id: str, order: str):
    """Установить порядок сортировки объектов пользователя"""
    user_info = await get_user(str(user_id))
    if not user_info:
        user_info = {}
    user_info["sort_order"] = order
    await save_user(str(user_id), user_info)

async def get_user_last_autopublish_date(user_id: str) -> Optional[str]:
    """Получить дату последней автопубликации пользователя"""
    objects = await load_json("objects.json")
    last_date = None
    
    for obj_id, obj_data in objects.items():
        if obj_data.get("user_id") == str(user_id):
            pub_date = obj_data.get("publication_date", "")
            if pub_date:
                try:
                    # Парсим дату публикации
                    pub_dt = parse_moscow_datetime(pub_date, "%Y-%m-%d %H:%M:%S")
                    if last_date is None or pub_dt > parse_moscow_datetime(last_date, "%Y-%m-%d %H:%M:%S"):
                        last_date = pub_date
                except:
                    pass
    
    return last_date

async def delete_object(object_id: str):
    """Удалить объект"""
    objects = await load_json("objects.json")
    if object_id in objects:
        del objects[object_id]
        await save_json("objects.json", objects)

async def get_chats() -> Dict:
    """Получить все чаты"""
    return await load_json("chats.json")

async def add_chat(chat_id: str, chat_data: Dict):
    """Добавить чат"""
    chats = await load_json("chats.json")
    chats[str(chat_id)] = chat_data
    await save_json("chats.json", chats)

async def increment_chat_publications(chat_id: str):
    """Увеличить счетчик публикаций чата"""
    chats = await load_json("chats.json")
    if str(chat_id) in chats:
        chats[str(chat_id)]["total_publications"] = chats[str(chat_id)].get("total_publications", 0) + 1
        await save_json("chats.json", chats)

async def delete_chat(chat_id: str):
    """Удалить чат"""
    chats = await load_json("chats.json")
    if str(chat_id) in chats:
        del chats[str(chat_id)]
        await save_json("chats.json", chats)
        return True
    return False

async def get_districts_config() -> Dict:
    """Получить конфигурацию районов"""
    # Проверяем оба файла для совместимости
    config1 = await load_json("districts_config.json")
    config2 = await load_json("districts.json")
    
    # Используем districts_config.json как основной, если он существует
    if config1:
        return config1
    elif config2:
        # Если есть только districts.json, сохраняем в districts_config.json
        await save_json("districts_config.json", config2)
        return config2
    else:
        # Если файлов нет, создаем пустой
        await ensure_file_exists("districts_config.json", {})
        return {}

async def save_districts_config(districts_config: Dict):
    """Сохранить конфигурацию районов"""
    await save_json("districts_config.json", districts_config)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def create_fake_context(bot):
    """Создать FakeContext для публикации"""
    class FakeContext:
        def __init__(self, bot):
            self.bot = bot
    return FakeContext(bot)

def replace_digits_with_special(text: str) -> str:
    """Заменить цифры на специальные символы 𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"""
    digit_map = {
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰',
        '5': '𝟱', '6': '𝟲', '7': '𝟳', '8': '𝟴', '9': '𝟵'
    }
    result = ''
    for char in text:
        result += digit_map.get(char, char)
    return result

def get_parse_mode_for_text(text: str):
    """Получить parse_mode для текста, если в нём есть ссылки"""
    if text and "<a href=" in text:
        return ParseMode.HTML
    return None

async def format_publication_text(obj: Dict, user_info: Dict = None, is_preview: bool = False) -> str:
    """Сформировать текст публикации объекта в новом формате
    
    Args:
        obj: Объект недвижимости
        user_info: Информация о пользователе
        is_preview: Если True, футер не будет показан (для превью редактирования)
    """
    # Создаем копию объекта, чтобы не изменять оригинал
    obj_copy = obj.copy()
    if is_preview:
        obj_copy["_is_preview"] = True
    
    lines = []
    
    # Цена: 🔑¦ 𝟲𝟲𝟲
    price = obj.get('price', 0)
    price_str = replace_digits_with_special(str(int(price)) if isinstance(price, float) else str(price))
    lines.append(f"🔑¦ {price_str}")
    
    # Тип комнат: 🏠¦1к
    rooms_type = obj.get('rooms_type', '')
    if rooms_type:
        lines.append(f"🏠¦{rooms_type}")
    
    # Районы - нужно разделить на родительские и второго уровня
    districts = obj.get('districts', [])
    districts_config = await get_districts_config()
    
    # Собираем родительские районы (те, что указаны в districts_config[district])
    parent_districts = set()
    second_level_districts = []
    first_level_districts = []
    
    for district in districts:
        if district in districts_config:
            parents = districts_config[district]
            if parents:
                # У этого района есть родители - это район второго уровня
                parent_districts.update(parents)
                second_level_districts.append(district)
            else:
                # Если нет родителей, это район первого уровня
                first_level_districts.append(district)
        else:
            # Если района нет в конфиге, считаем его районом первого уровня
            first_level_districts.append(district)
    
    # Районы первого уровня (🗺) - если район один, показываем один
    if len(first_level_districts) == 1:
        lines.append(f"🗺¦{first_level_districts[0]}")
    elif len(first_level_districts) > 1:
        lines.append(f"🗺¦{', '.join(first_level_districts)}")
    
    # Площадь: 𝙈 ²¦69
    area = obj.get('area', '')
    if area:
        area_str = replace_digits_with_special(area)
        lines.append(f"𝙈 ²¦{area_str}")
    
    # Этаж: 📐¦6/9
    floor = obj.get('floor', '')
    if floor:
        floor_str = replace_digits_with_special(floor)
        lines.append(f"📐¦{floor_str}")
    
    # Ремонт: 🛋¦Хороший ремонт
    renovation = obj.get('renovation', '')
    if renovation:
        lines.append(f"🛋¦{renovation}")
    
    # Адрес: 📍¦пушкина 123 (без замены цифр)
    address = obj.get('address', '')
    if address:
        lines.append(f"📍¦{address}")
    
    # Родительские районы (🗾) - если есть
    if parent_districts:
        parent_list = list(parent_districts)
        if len(parent_list) == 1:
            lines.append(f"🗾¦{parent_list[0]}")
        else:
            lines.append(f"🗾¦{', '.join(parent_list)}")
    
    # Пустая строка перед комментарием
    lines.append("")
    
    # Комментарий: 📝¦ текст
    comment = obj.get('comment', '')
    if comment:
        lines.append(f"📝¦")
        lines.append(comment)
    
    # Футер (показываем только если включен в настройках пользователя и это не превью редактирования)
    show_footer = False
    is_preview = obj_copy.get("_is_preview", False)  # Флаг для превью редактирования
    if user_info and not is_preview:
        show_footer = user_info.get("show_footer", False)
    
    if show_footer:
        lines.append("")
        lines.append("🔑¦<a href=\"http://t.me/keyskrd\">Ключи</a>")
        lines.append("🏢¦<a href=\"http://t.me/MasterKeyRobot\">@MasterKeyRobot</a>")
        lines.append("🗂¦<a href=\"https://t.me/addlist/QDGm9RwOldE4YzM6\">Папка со всеми чатами</a>")
        lines.append("")
    
    # Хэштеги (между футером и контактами)
    hashtags = []
    suffix = await get_hashtag_suffix()
    
    # Хэштег для типа комнат
    rooms_type = obj.get('rooms_type', '')
    if rooms_type:
        hashtags.append(generate_room_hashtag(rooms_type, suffix))
    
    # Хэштеги для районов
    for district in districts:
        hashtags.append(generate_district_hashtag(district, suffix))
    
    # Хэштег для ценового диапазона
    price = obj.get('price', 0)
    price_ranges = await get_price_ranges()
    for range_name, range_values in price_ranges.items():
        if range_values[0] <= price < range_values[1]:
            hashtags.append(generate_price_range_hashtag(range_name, suffix))
            break
    
    # Добавляем хэштеги между футером и контактами
    if hashtags:
        lines.append(" ".join(hashtags))
        lines.append("")
    
    # Контакты
    phone = obj.get('phone_number', '')
    if not phone and user_info:
        phone = user_info.get('phone_number', '')
    
    contact_name = obj.get('contact_name', '')
    show_username = obj.get('show_username', False)
    
    if contact_name or phone or (show_username and user_info and user_info.get('username')):
        if not hashtags:
            lines.append("")  # Пустая строка перед контактами, если нет хэштегов
        if contact_name:
            contact_name_str = replace_digits_with_special(contact_name)
            lines.append(f"🕴🏻¦{contact_name_str}")
        if phone:
            # Телефон без замены цифр - обычные цифры
            lines.append(f"☎️¦{phone}")
        if show_username and user_info and user_info.get('username'):
            username_str = replace_digits_with_special(user_info.get('username'))
            lines.append(f"📩¦@{username_str}")
    
    # Показываем родительские районы в конце (🗺)
    if parent_districts:
        parent_list = list(parent_districts)
        if len(parent_list) == 1:
            lines.append(f"🗺¦ {parent_list[0]}")
        else:
            lines.append(f"🗺¦ {', '.join(parent_list)}")
    
    # Показываем районы второго уровня в конце (🗾), если их больше одного
    if len(second_level_districts) > 1:
        lines.append(f"🗾¦ {', '.join(second_level_districts)}")
    
    return "\n".join(lines)

async def get_hashtag_suffix() -> str:
    """Получить суффикс хэштегов"""
    config = await load_json("config_flags.json")
    return config.get("hashtag_suffix", "_ф")

async def save_hashtag_suffix(suffix: str):
    """Сохранить суффикс хэштегов"""
    config = await load_json("config_flags.json")
    config["hashtag_suffix"] = suffix
    await save_json("config_flags.json", config)

def generate_district_hashtag(district_name: str, suffix: str = "_ф") -> str:
    """Генерировать хэштег для района
    
    Примеры:
    - "Прикубанский" -> "#_Прикубанский_ф"
    - "Белые Росы" -> "#_БелыеРосы_ф"
    """
    # Убираем пробелы и объединяем слова
    hashtag_name = district_name.replace(" ", "")
    return f"#_{hashtag_name}{suffix}"

def generate_room_hashtag(room_type: str, suffix: str = "_ф") -> str:
    """Генерировать хэштег для типа комнат
    
    Примеры:
    - "Студия" -> "#_студия_ст_ф"
    - "1к" -> "#_однокомнатная_1к_ф"
    - "2к" -> "#_двухкомнатная_2к_ф"
    """
    room_mapping = {
        "Студия": "студия_ст",
        "1к": "однокомнатная_1к",
        "2к": "двухкомнатная_2к",
        "3к": "трехкомнатная_3к",
        "4+к": "четырехкомнатная_4к",
        "4к": "четырехкомнатная_4к",
        "Дом": "дом"
    }
    hashtag_name = room_mapping.get(room_type, room_type.lower().replace(" ", "_").replace("+", ""))
    return f"#_{hashtag_name}{suffix}"

def generate_price_range_hashtag(range_name: str, suffix: str = "_ф") -> str:
    """Генерировать хэштег для ценового диапазона
    
    Примеры:
    - "до 4000" -> "#_до_4000_ф"
    - "4000-6000" -> "#_4000_6000_ф"
    """
    # Заменяем пробелы и дефисы на подчеркивания
    hashtag_name = range_name.replace(" ", "_").replace("-", "_")
    return f"#_{hashtag_name}{suffix}"

async def get_price_ranges() -> Dict:
    """Получить ценовые диапазоны"""
    await ensure_file_exists("price_ranges.json", {
        "до 4000": [0, 4000],
        "4000-6000": [4000, 6000],
        "6000-8000": [6000, 8000],
        "8000-10000": [8000, 10000],
        "10000+": [10000, 999999]
    })
    return await load_json("price_ranges.json")

async def save_price_ranges(ranges: Dict):
    """Сохранить ценовые диапазоны"""
    await save_json("price_ranges.json", ranges)

async def get_rooms_config() -> List[str]:
    """Получить конфигурацию типов комнат"""
    await ensure_file_exists("rooms_config.json", ["Студия", "1к", "2к", "3к", "4+к", "Дом"])
    rooms_data = await load_json("rooms_config.json")
    if isinstance(rooms_data, list):
        return rooms_data
    return rooms_data.get("rooms", ["Студия", "1к", "2к", "3к", "4+к", "Дом"])

async def save_rooms_config(rooms: List[str]):
    """Сохранить конфигурацию типов комнат"""
    await save_json("rooms_config.json", rooms)

async def get_subscription_check_flag() -> bool:
    """Получить флаг проверки подписки"""
    try:
        flags = await load_json("config_flags.json")
        return flags.get("CHECK_SUBSCRIPTION_ENABLED", True)
    except:
        return True

async def set_subscription_check_flag(value: bool):
    """Установить флаг проверки подписки"""
    flags = await load_json("config_flags.json")
    flags["CHECK_SUBSCRIPTION_ENABLED"] = value
    await save_json("config_flags.json", flags)

# ==================== ФУНКЦИИ РАБОТЫ С РОЛЯМИ ====================
async def get_roles_config() -> List[str]:
    """Получить список всех ролей"""
    default_roles = [ROLE_START, ROLE_BROKE, ROLE_BEGINNER, ROLE_FREE, ROLE_FREEPREMIUM, ROLE_PREMIUM, ROLE_PROTIME]
    await ensure_file_exists("roles_config.json", default_roles)
    roles_data = await load_json("roles_config.json")
    if isinstance(roles_data, list):
        return roles_data
    return roles_data.get("roles", default_roles)

async def save_roles_config(roles: List[str]):
    """Сохранить список ролей"""
    await save_json("roles_config.json", roles)

async def get_user_role(user_id: str) -> str:
    """Получить роль пользователя"""
    user = await get_user(str(user_id))
    if not user:
        return ROLE_START
    return user.get("role", ROLE_START)

async def set_user_role(user_id: str, role: str):
    """Установить роль пользователя"""
    user = await get_user(str(user_id))
    if not user:
        await update_user_activity(str(user_id))
        user = await get_user(str(user_id))
    user["role"] = role
    await save_user(str(user_id), user)
    await log_action("USER_ROLE_CHANGED", int(user_id) if user_id.isdigit() else None, 
                     user.get("username"), f"New role: {role}")

async def can_schedule_publication(user_id: str) -> bool:
    """Проверить, может ли пользователь планировать публикации"""
    role = await get_user_role(str(user_id))
    # Планировать автопубликацию могут freepremium, premium и protime
    return role in [ROLE_FREEPREMIUM, ROLE_PREMIUM, ROLE_PROTIME]

async def can_choose_time_slot(user_id: str) -> bool:
    """Проверить, может ли пользователь выбирать временные слоты"""
    role = await get_user_role(str(user_id))
    # Слоты 12-22 доступны для premium и protime
    return role in [ROLE_PREMIUM, ROLE_PROTIME]

# ==================== ФУНКЦИИ РАБОТЫ С АВТОПУБЛИКАЦИЕЙ ====================
async def get_user_autopublish_settings(user_id: str) -> Dict:
    """Получить настройки автопубликации пользователя"""
    user = await get_user(str(user_id))
    if not user:
        return {
            "enabled": False,
            "time_type": None,  # "vip", "default", "slot"
            "slot_time": None  # Для слотов: "HH:MM"
        }
    
    return {
        "enabled": user.get("autopublish_enabled", False),
        "time_type": user.get("autopublish_time_type", None),
        "slot_time": user.get("autopublish_slot_time", None)
    }

async def set_user_autopublish_settings(user_id: str, enabled: bool = None, time_type: str = None, slot_time: str = None):
    """Установить настройки автопубликации пользователя"""
    user = await get_user(str(user_id))
    if not user:
        await update_user_activity(str(user_id))
        user = await get_user(str(user_id))
    
    if enabled is not None:
        user["autopublish_enabled"] = enabled
    if time_type is not None:
        user["autopublish_time_type"] = time_type
    if slot_time is not None:
        user["autopublish_slot_time"] = slot_time
    
    await save_user(str(user_id), user)


async def toggle_user_autopublish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключатель общей автопубликации в меню настроек"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_role = await get_user_role(str(user.id))
    
    # Доступ для freepremium, premium и Pro Time
    if user_role not in [ROLE_FREEPREMIUM, ROLE_PREMIUM, ROLE_PROTIME]:
        await query.answer("Общая автопубликация доступна только для freepremium, premium и Pro Time.", show_alert=True)
        return
    
    settings = await get_user_autopublish_settings(str(user.id))
    current = settings.get("enabled", False)
    new_value = not current
    
    await set_user_autopublish_settings(str(user.id), enabled=new_value)
    
    # Обновляем меню
    await auto_publish_settings(update, context)

async def get_object_autopublish_enabled(object_id: str) -> bool:
    """Получить статус автопубликации для объекта"""
    obj = await get_object(object_id)
    if not obj:
        return False
    return obj.get("auto_publish_enabled", False)

async def set_object_autopublish_enabled(object_id: str, enabled: bool):
    """Установить статус автопубликации для объекта"""
    await update_object(object_id, {"auto_publish_enabled": enabled})

async def get_user_objects_for_autopublish(user_id: str) -> List[Dict]:
    """Получить все объекты пользователя с включенной автопубликацией"""
    objects = await load_json("objects.json")
    user_objects = []
    total_user_objects = 0
    
    for obj_id, obj in objects.items():
        if obj.get("user_id") == str(user_id):
            total_user_objects += 1
            auto_publish_enabled = obj.get("auto_publish_enabled", False)
            status = obj.get("status", "")
            
            if auto_publish_enabled and status in ["черновик", "опубликовано"]:
                user_objects.append({
                    "object_id": obj_id,
                    "object": obj
                })
    
    if user_id.isdigit():
        await log_action("AUTOPUBLISH_OBJECTS_CHECK", int(user_id), None, 
                       f"Total objects: {total_user_objects}, Objects with autopublish enabled: {len(user_objects)}")
    
    return user_objects

# ==================== ФУНКЦИИ РАБОТЫ С ВРЕМЕННЫМИ СЛОТАМИ ====================
def generate_time_slots() -> List[Dict[str, Any]]:
    """Генерировать список временных слотов"""
    slots = []
    
    # Слоты 8 (для определенных категорий)
    slots.append({
        "slot_id": "slot_0800",
        "time": "08:00",
        "type": SLOT_CATEGORY_8_9,
        "available": True
    })
    
    # Слоты 9-12 (по умолчанию - общая очередь)
    for hour in [9, 10, 11, 12]:
        slots.append({
            "slot_id": f"slot_{hour:02d}00",
            "time": f"{hour:02d}:00",
            "type": SLOT_DEFAULT_9_12,
            "available": True
        })
    
    # Слоты 12-22 с интервалом 15 минут
    for hour in range(12, 23):
        for minute in [0, 15, 30, 45]:
            if hour == 12 and minute == 0:
                continue  # Уже добавлен выше
            slots.append({
                "slot_id": f"slot_{hour:02d}{minute:02d}",
                "time": f"{hour:02d}:{minute:02d}",
                "type": SLOT_CUSTOM_12_22,
                "available": True
            })
    
    return slots

async def get_available_slots(date: str = None, user_id: str = None) -> List[Dict[str, Any]]:
    """Получить доступные слоты на дату
    
    Для VIP (8-9) и по умолчанию (9-12) - слоты всегда доступны (общая очередь)
    Для слотов 12-22 - проверяем, не занят ли слот другим пользователем
    """
    if date is None:
        date = format_moscow_datetime(format_str="%Y-%m-%d")
    
    # Загружаем забронированные слоты
    scheduled = await load_json("scheduled_publications.json")
    
    # Генерируем все слоты
    all_slots = generate_time_slots()
    
    # Помечаем занятые слоты
    for slot in all_slots:
        slot_key = f"{date}_{slot['slot_id']}"
        
        # Для VIP и по умолчанию - слоты всегда доступны (общая очередь)
        if slot["type"] in [SLOT_CATEGORY_8_9, SLOT_DEFAULT_9_12]:
            slot["available"] = True
            continue
        
        # Для слотов 12-22 - проверяем, не занят ли другим пользователем
        if slot["type"] == SLOT_CUSTOM_12_22:
            if slot_key in scheduled:
                booked_user = scheduled[slot_key].get("user_id")
                # Если слот занят другим пользователем - недоступен
                if user_id and booked_user != str(user_id):
                    slot["available"] = False
                    slot["booked_by"] = booked_user
                # Если слот занят этим пользователем - доступен
                elif user_id and booked_user == str(user_id):
                    slot["available"] = True
                # Если слот занят и user_id не указан - недоступен
                elif not user_id:
                    slot["available"] = False
                    slot["booked_by"] = booked_user
                else:
                    slot["available"] = True
            else:
                slot["available"] = True
    
    return all_slots

async def book_time_slot(date: str, slot_id: str, user_id: str, object_id: str = None) -> bool:
    """Забронировать временной слот для пользователя (для автопубликации)"""
    await ensure_file_exists("scheduled_publications.json", {})
    scheduled = await load_json("scheduled_publications.json")
    slot_key = f"{date}_{slot_id}"
    
    # Проверяем, не занят ли слот другим пользователем
    if slot_key in scheduled:
        existing_user = scheduled[slot_key].get("user_id")
        # Если слот уже забронирован этим пользователем, разрешаем
        if existing_user != str(user_id):
            return False
    
    # Бронируем слот для пользователя
    scheduled[slot_key] = {
        "user_id": str(user_id),
        "object_id": object_id,  # Может быть None для автопубликации
        "date": date,
        "slot_id": slot_id,
        "booked_at": format_moscow_datetime()
    }
    
    await save_json("scheduled_publications.json", scheduled)
    return True

async def release_time_slot(date: str, slot_id: str, user_id: str):
    """Освободить временной слот пользователя"""
    await ensure_file_exists("scheduled_publications.json", {})
    scheduled = await load_json("scheduled_publications.json")
    slot_key = f"{date}_{slot_id}"
    
    if slot_key in scheduled and scheduled[slot_key].get("user_id") == str(user_id):
        del scheduled[slot_key]
        await save_json("scheduled_publications.json", scheduled)
        return True
    
    return False

async def get_scheduled_publications() -> List[Dict[str, Any]]:
    """Получить все запланированные публикации"""
    await ensure_file_exists("scheduled_publications.json", {})
    scheduled = await load_json("scheduled_publications.json")
    objects = await load_json("objects.json")
    
    result = []
    for slot_key, slot_data in scheduled.items():
        object_id = slot_data.get("object_id")
        if object_id and object_id in objects:
            obj = objects[object_id]
            if obj.get("status") == "запланировано":
                result.append({
                    "slot_key": slot_key,
                    "object_id": object_id,
                    "date": slot_data.get("date"),
                    "slot_id": slot_data.get("slot_id"),
                    "user_id": slot_data.get("user_id"),
                    "object": obj
                })
    
    return result

# ==================== ФУНКЦИИ ОЧЕРЕДИ ПУБЛИКАЦИЙ ====================
# Глобальная очередь публикаций
publication_queue = asyncio.Queue()
last_message_time = {}  # {chat_id: timestamp} для отслеживания лимитов

async def add_to_publication_queue(chat_id: str, message_data: Dict[str, Any], priority: int = 0):
    """Добавить публикацию в очередь"""
    await publication_queue.put({
        "chat_id": chat_id,
        "message_data": message_data,
        "priority": priority,
        "timestamp": get_moscow_time().timestamp()
    })

async def get_next_publication_time(chat_id: str) -> float:
    """Получить время следующей возможной публикации с учетом лимитов"""
    now = get_moscow_time().timestamp()
    
    if chat_id not in last_message_time:
        return now
    
    last_time = last_message_time[chat_id]
    next_time = last_time + TELEGRAM_MESSAGE_INTERVAL
    
    if next_time <= now:
        return now
    
    return next_time

async def send_publication_with_rate_limit(context: Any, chat_id: str, message_data: Dict[str, Any]):
    """Отправить публикацию с учетом лимитов Telegram с расширенным логированием"""
    # Ждем, пока не пройдет интервал
    next_time = await get_next_publication_time(chat_id)
    now = get_moscow_time().timestamp()
    
    if next_time > now:
        wait_time = next_time - now
        logger.debug(f"RATE_LIMIT_WAIT | Chat: {chat_id} | Wait: {wait_time:.2f}s")
        await asyncio.sleep(wait_time)
    
    # Отправляем сообщение
    try:
        if message_data["type"] == "photo":
            logger.info(f"SENDING_PHOTO | Chat: {chat_id} | Caption length: {len(message_data.get('caption', ''))}")
            caption = message_data.get("caption")
            # Проверяем, есть ли ссылки в тексте (формат <a href="url">текст</a>)
            parse_mode = None
            if caption and "<a href=" in caption:
                parse_mode = ParseMode.HTML
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=message_data["photo"],
                caption=caption,
                parse_mode=parse_mode
            )
            
        elif message_data["type"] == "video":
            logger.info(f"SENDING_VIDEO | Chat: {chat_id} | Caption length: {len(message_data.get('caption', ''))}")
            caption = message_data.get("caption")
            # Проверяем, есть ли ссылки в тексте (формат <a href="url">текст</a>)
            parse_mode = None
            if caption and "<a href=" in caption:
                parse_mode = ParseMode.HTML
            await context.bot.send_video(
                chat_id=chat_id,
                video=message_data["video"],
                caption=caption,
                parse_mode=parse_mode
            )
            
        elif message_data["type"] == "media_group":
            media_list = message_data["media"]
            media_count = len(media_list)
            
            # Детальное логирование media_group
            logger.info(f"SENDING_MEDIA_GROUP | Chat: {chat_id} | Media count: {media_count}")
            
            for i, media in enumerate(media_list):
                media_type = "photo" if isinstance(media, InputMediaPhoto) else "video"
                caption_len = len(media.caption) if media.caption else 0
                parse_mode = media.parse_mode if media.parse_mode else "None"
                logger.debug(f"MEDIA_ITEM_{i} | Type: {media_type} | "
                           f"Caption length: {caption_len} | Parse mode: {parse_mode}")
            
            try:
                result = await context.bot.send_media_group(
                    chat_id=chat_id,
                    media=media_list
                )
                logger.info(f"MEDIA_GROUP_SENT | Chat: {chat_id} | Result count: {len(result)}")
                await log_action("SEND_MEDIA_GROUP_SUCCESS", None, None, f"Chat: {chat_id}, Sent messages: {len(result) if result else 0}")
                
            except Exception as e:
                logger.error(f"MEDIA_GROUP_ERROR | Chat: {chat_id} | Error: {str(e)} | "
                           f"Error type: {type(e).__name__}")
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"MEDIA_GROUP_ERROR_TRACEBACK | Chat: {chat_id} | Traceback: {error_traceback}")
                await log_action("SEND_MEDIA_GROUP_ERROR", None, None, f"Chat: {chat_id}, Error: {str(e)}, Error type: {type(e).__name__}")
                # Пробрасываем исключение дальше - всегда отправляем все целиком
                raise
                
        elif message_data["type"] == "text":
            logger.info(f"SENDING_TEXT | Chat: {chat_id} | Text length: {len(message_data['text'])}")
            text = message_data["text"]
            # Проверяем, есть ли ссылки в тексте (формат <a href="url">текст</a>)
            parse_mode = None
            if text and "<a href=" in text:
                parse_mode = ParseMode.HTML
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
        
        # Обновляем время последнего сообщения
        last_message_time[chat_id] = get_moscow_time().timestamp()
        logger.debug(f"MESSAGE_SENT_SUCCESS | Chat: {chat_id} | Time updated")
        return True
        
    except Exception as e:
        logger.error(f"PUBLICATION_SEND_ERROR | Chat: {chat_id} | Error: {str(e)} | "
                   f"Error type: {type(e).__name__}")
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"PUBLICATION_SEND_ERROR_TRACEBACK | Chat: {chat_id} | Traceback: {error_traceback}")
        await log_action("PUBLICATION_SEND_ERROR", None, None, f"Chat: {chat_id}, Error: {str(e)}")
        return False

# ==================== ФОНОВАЯ ЗАДАЧА ДЛЯ ЗАПЛАНИРОВАННЫХ ПУБЛИКАЦИЙ ====================
async def process_scheduled_publications(app: Application):
    """Обработка запланированных публикаций"""
    while True:
        try:
            now = get_moscow_time()
            scheduled_pubs = await get_scheduled_publications()
            
            for pub in scheduled_pubs:
                obj = pub["object"]
                scheduled_time_str = obj.get("scheduled_time")
                
                if not scheduled_time_str:
                    continue
                
                try:
                    scheduled_time = parse_moscow_datetime(scheduled_time_str, "%Y-%m-%d %H:%M")
                except:
                    continue
                
                # Проверяем, наступило ли время публикации (с допуском 1 минута)
                if now >= scheduled_time and (now - scheduled_time).total_seconds() < 60:
                    # Публикуем объект
                    await log_action("SCHEDULED_PUBLICATION_START", int(pub["user_id"]), None, 
                                   f"Object: {pub['object_id']}, Time: {scheduled_time_str}")
                    
                    # Формируем данные для публикации
                    user_info = await get_user(pub["user_id"])
                    phone = obj.get('phone_number', '')
                    if not phone and user_info:
                        phone = user_info.get('phone_number', '')
                    
                    # Формирование текста публикации
                    publication_text = await format_publication_text(obj, user_info)
                    
                    # Определение целевых чатов
                    target_chats = await get_target_chats_for_object(obj)
                    
                    # Публикация в чаты
                    published_count = 0
                    media_files = obj.get('media_files', [])
                    
                    # Создаем контекст для публикации
                    fake_context = create_fake_context(app.bot)
                    
                    for chat_id in target_chats:
                        try:
                            if media_files:
                                media_group = []
                                parse_mode = get_parse_mode_for_text(publication_text)
                                for media in media_files[:10]:
                                    caption = publication_text if len(media_group) == 0 else None
                                    if media['type'] == 'photo':
                                        media_group.append(InputMediaPhoto(media['file_id'], caption=caption, parse_mode=parse_mode if caption else None))
                                    elif media['type'] == 'video':
                                        media_group.append(InputMediaVideo(media['file_id'], caption=caption, parse_mode=parse_mode if caption else None))
                                
                                if len(media_group) == 1:
                                    if isinstance(media_group[0], InputMediaPhoto):
                                        message_data = {
                                            "type": "photo",
                                            "photo": media_group[0].media,
                                            "caption": publication_text
                                        }
                                    else:
                                        message_data = {
                                            "type": "video",
                                            "video": media_group[0].media,
                                            "caption": publication_text
                                        }
                                    await send_publication_with_rate_limit(fake_context, chat_id, message_data)
                                else:
                                    message_data = {
                                        "type": "media_group",
                                        "media": media_group,
                                        "caption": publication_text if len(media_group) < len(media_files) else None
                                    }
                                    await send_publication_with_rate_limit(fake_context, chat_id, message_data)
                            else:
                                message_data = {
                                    "type": "text",
                                    "text": publication_text
                                }
                                await send_publication_with_rate_limit(fake_context, chat_id, message_data)
                            
                            await increment_chat_publications(chat_id)
                            published_count += 1
                            
                            await log_action("SCHEDULED_OBJECT_PUBLISHED", int(pub["user_id"]), None, 
                                           f"Chat: {chat_id}, Object: {pub['object_id']}")
                        except Exception as e:
                            await log_action("SCHEDULED_PUBLICATION_ERROR", int(pub["user_id"]), None, 
                                           f"Chat: {chat_id}, Error: {str(e)}")
                    
                    # Обновление объекта
                    await update_object(pub["object_id"], {
                        "status": "опубликовано",
                        "publication_date": format_moscow_datetime(now),
                        "target_chats": target_chats,
                        "phone_number": phone
                    })
                    
                    # Обновление статистики пользователя
                    if user_info:
                        user_info["total_publications"] = user_info.get("total_publications", 0) + 1
                        await save_user(pub["user_id"], user_info)
                    
                    # Удаление из запланированных
                    scheduled = await load_json("scheduled_publications.json")
                    slot_key = pub["slot_key"]
                    if slot_key in scheduled:
                        del scheduled[slot_key]
                        await save_json("scheduled_publications.json", scheduled)
                    
                    await log_action("SCHEDULED_PUBLICATION_COMPLETE", int(pub["user_id"]), None, 
                                   f"Object: {pub['object_id']}, Published to {published_count} chats")
            
            # Проверяем каждую минуту
            await asyncio.sleep(60)
        except Exception as e:
            await log_action("SCHEDULED_PUBLICATIONS_ERROR", None, None, f"Error: {str(e)}")
            await asyncio.sleep(60)


async def process_autopublish_queues(app: Application):
    """Обработка ежедневной публикации объектов из очередей автопубликации"""
    processed_vip_today = False
    processed_default_today = False
    processed_slots_today = {}  # Словарь для отслеживания обработанных слотов
    
    while True:
        try:
            # Получаем текущее время в московском часовом поясе
            now = get_moscow_time()
            now_utc = datetime.now(timezone.utc)
            now_utc_moscow = now_utc.astimezone(MOSCOW_TZ)
            
            current_time = format_moscow_datetime(now, "%H:%M")
            current_date = format_moscow_datetime(now, "%Y-%m-%d")
            current_minute = now.minute
            current_hour = now.hour
            current_second = now.second
            
            # Логируем текущее время для отладки (раз в минуту)
            if current_second == 0:
                await log_action("AUTOPUBLISH_TIME_CHECK", None, None, 
                               f"Moscow time: {current_time}, UTC time: {format_moscow_datetime(now_utc_moscow, '%H:%M')}, Date: {current_date}")
            
            # Получаем всех пользователей с включенной автопубликацией
            users = await load_json("users.json")
            objects = await load_json("objects.json")
            
            # Обработка VIP очереди (8:00-8:01) - проверяем в течение первой минуты часа
            if current_hour == 8 and current_minute == 0 and current_second <= 30 and not processed_vip_today:
                await log_action("AUTOPUBLISH_VIP_START", None, None, f"Moscow time: {current_time}, Second: {current_second}, UTC: {format_moscow_datetime(now_utc_moscow, '%H:%M')}")
                await process_autopublish_queue(app, users, objects, "vip", "08:00")
                processed_vip_today = True
                await log_action("AUTOPUBLISH_VIP_COMPLETE", None, None, f"Time: {current_time}")
            
            # Обработка очереди по умолчанию (9:00-9:01) - проверяем в течение первой минуты часа
            if current_hour == 9 and current_minute == 0 and current_second <= 30 and not processed_default_today:
                await log_action("AUTOPUBLISH_DEFAULT_START", None, None, f"Moscow time: {current_time}, Second: {current_second}, UTC: {format_moscow_datetime(now_utc_moscow, '%H:%M')}")
                await process_autopublish_queue(app, users, objects, "default", "09:00")
                processed_default_today = True
                await log_action("AUTOPUBLISH_DEFAULT_COMPLETE", None, None, f"Time: {current_time}")
            
            # Обработка слотов (12:00 - 22:00, каждые 15 минут)
            # Проверяем секунды, чтобы обрабатывать слот только в начале минуты (0-30 секунд)
            current_minute_str = current_time[3:]
            if current_minute_str in ["00", "15", "30", "45"]:  # Каждые 15 минут
                hour = int(current_time[:2])
                if 12 <= hour < 23:
                    # Проверяем, не обработан ли уже этот слот сегодня
                    slot_key = f"{current_date}_{current_time}"
                    # Обрабатываем слот только в начале минуты (первые 30 секунд) или если еще не обработан
                    if slot_key not in processed_slots_today:
                        if current_second <= 30:
                            await log_action("AUTOPUBLISH_SLOT_START", None, None, f"Time: {current_time}, Second: {current_second}, Hour: {hour}, Minute: {current_minute_str}")
                            await process_autopublish_queue(app, users, objects, "slot", current_time)
                            processed_slots_today[slot_key] = True
                            await log_action("AUTOPUBLISH_SLOT_COMPLETE", None, None, f"Time: {current_time}")
                        else:
                            await log_action("AUTOPUBLISH_SLOT_TOO_LATE", None, None, f"Time: {current_time}, Second: {current_second} (too late, should be <= 30)")
                    else:
                        await log_action("AUTOPUBLISH_SLOT_ALREADY_PROCESSED", None, None, f"Time: {current_time}, Slot key: {slot_key}")
            
            # Сбрасываем флаги при смене дня (в начале нового дня, после 00:00:30)
            if current_hour == 0 and current_minute == 0 and current_second > 30:
                if processed_vip_today or processed_default_today or len(processed_slots_today) > 0:
                    await log_action("AUTOPUBLISH_RESET_FLAGS", None, None, f"Resetting flags for new day at Moscow time: {current_time}, UTC: {format_moscow_datetime(now_utc_moscow, '%H:%M')}")
                    processed_vip_today = False
                    processed_default_today = False
                    processed_slots_today = {}
            
            # Проверяем каждые 10 секунд для более точной обработки слотов
            await asyncio.sleep(10)
        except Exception as e:
            await log_action("AUTOPUBLISH_QUEUES_ERROR", None, None, f"Error: {str(e)}")
            import traceback
            print(f"AUTOPUBLISH_QUEUES_ERROR: {traceback.format_exc()}")
            await asyncio.sleep(60)


async def process_autopublish_queue(app: Application, users: Dict, objects: Dict, queue_type: str, target_time: str):
    """Обработать очередь автопубликации определенного типа"""
    now = get_moscow_time()
    current_date = format_moscow_datetime(now, "%Y-%m-%d")
    
    await log_action("AUTOPUBLISH_QUEUE_START", None, None, 
                   f"Queue type: {queue_type}, Target time: {target_time}, Total users: {len(users)}")
    
    # Находим пользователей с нужным типом времени
    for user_id, user_data in users.items():
        autopublish_settings = await get_user_autopublish_settings(user_id)
        user_role = await get_user_role(str(user_id))
        
        await log_action("AUTOPUBLISH_USER_INITIAL_CHECK", int(user_id), user_data.get("username"), 
                       f"Enabled: {autopublish_settings.get('enabled')}, Time type: {autopublish_settings.get('time_type')}, Queue type: {queue_type}, Role: {user_role}")
        
        if not autopublish_settings.get("enabled"):
            await log_action("AUTOPUBLISH_USER_SKIP_DISABLED", int(user_id), user_data.get("username"), 
                           f"Autopublish disabled for user")
            continue
        
        if autopublish_settings.get("time_type") != queue_type:
            await log_action("AUTOPUBLISH_USER_SKIP_TIME_TYPE", int(user_id), user_data.get("username"), 
                           f"Time type mismatch: '{autopublish_settings.get('time_type')}' != '{queue_type}'")
            continue
        
        # Дополнительные ограничения по ролям
        if queue_type == "vip":
            # VIP очередь только для Pro Time
            if user_role != ROLE_PROTIME:
                await log_action("AUTOPUBLISH_USER_SKIP_ROLE_VIP", int(user_id), user_data.get("username"), 
                               f"Role {user_role} not allowed for VIP queue (required: {ROLE_PROTIME})")
                continue
        elif queue_type == "slot":
            # Слоты только для premium и Pro Time
            if user_role not in [ROLE_PREMIUM, ROLE_PROTIME]:
                await log_action("AUTOPUBLISH_USER_SKIP_ROLE_SLOT", int(user_id), user_data.get("username"), 
                               f"Role {user_role} not allowed for slot queue (required: {ROLE_PREMIUM} or {ROLE_PROTIME})")
                continue
        
        # Для слотов проверяем точное время
        if queue_type == "slot":
            slot_time = autopublish_settings.get("slot_time")
            # Нормализуем время (убираем пробелы, приводим к формату HH:MM)
            slot_time_normalized = slot_time.strip() if slot_time else None
            target_time_normalized = target_time.strip() if target_time else None
            
            await log_action("AUTOPUBLISH_SLOT_CHECK", int(user_id), user_data.get("username"), 
                           f"Checking slot: user_slot_time='{slot_time_normalized}' (original: '{slot_time}'), target_time='{target_time_normalized}' (original: '{target_time}'), enabled={autopublish_settings.get('enabled')}, time_type={autopublish_settings.get('time_type')}")
            
            if slot_time_normalized != target_time_normalized:
                await log_action("AUTOPUBLISH_SLOT_SKIP", int(user_id), user_data.get("username"), 
                               f"Slot time mismatch: '{slot_time_normalized}' != '{target_time_normalized}'")
                continue
            await log_action("AUTOPUBLISH_SLOT_MATCH", int(user_id), user_data.get("username"), 
                           f"Slot time match: '{slot_time_normalized}' == '{target_time_normalized}'")
        
        # Получаем объекты пользователя с включенной автопубликацией
        user_objects = await get_user_objects_for_autopublish(user_id)
        
        await log_action("AUTOPUBLISH_USER_CHECK", int(user_id), user_data.get("username"), 
                       f"Queue type: {queue_type}, Time: {target_time}, Objects found: {len(user_objects) if user_objects else 0}")
        
        if not user_objects:
            await log_action("AUTOPUBLISH_NO_OBJECTS", int(user_id), user_data.get("username"), 
                           f"Queue type: {queue_type}, Time: {target_time}")
            continue
        
        await log_action("AUTOPUBLISH_START", int(user_id), user_data.get("username"), 
                       f"Queue type: {queue_type}, Time: {target_time}, Objects: {len(user_objects)}")
        
        # Публикуем каждый объект
        for obj_data in user_objects:
            obj_id = obj_data["object_id"]
            obj = obj_data["object"]
            
            try:
                await log_action("AUTOPUBLISH_OBJECT_START", int(user_id), user_data.get("username"), 
                               f"Object: {obj_id}, Queue type: {queue_type}, Time: {target_time}")
                await publish_object_from_queue(app, obj_id, obj, user_id, user_data)
                await log_action("AUTOPUBLISH_OBJECT_SUCCESS", int(user_id), user_data.get("username"), 
                               f"Object: {obj_id}")
            except Exception as e:
                await log_action("AUTOPUBLISH_OBJECT_ERROR", int(user_id), user_data.get("username"), 
                               f"Object: {obj_id}, Error: {str(e)}")
                import traceback
                print(f"AUTOPUBLISH_OBJECT_ERROR: {traceback.format_exc()}")


async def publish_object_from_queue(app: Application, object_id: str, obj: Dict, user_id: str, user_info: Dict):
    """Опубликовать объект из очереди автопубликации"""
    # Формируем данные для публикации
    phone = obj.get('phone_number', '')
    if not phone and user_info:
        phone = user_info.get('phone_number', '')
    
    # Формирование текста публикации
    publication_text = await format_publication_text(obj, user_info)
    
    # Определение целевых чатов
    target_chats = await get_target_chats_for_object(obj)
    
    # Публикация в чаты
    published_count = 0
    media_files = obj.get('media_files', [])
    
    # Создаем контекст для публикации
    fake_context = create_fake_context(app.bot)
    
    for chat_id in target_chats:
        max_retries = 3
        retry_count = 0
        success = False
        
        while retry_count < max_retries and not success:
            try:
                if media_files:
                    media_group = []
                    for media_file in media_files:
                        file_id = media_file.get("file_id")
                        media_type = media_file.get("type")
                        
                        parse_mode = get_parse_mode_for_text(publication_text)
                        caption = publication_text if len(media_group) == 0 else None
                        if media_type == "photo":
                            media_group.append(InputMediaPhoto(media=file_id, caption=caption, parse_mode=parse_mode if caption else None))
                        elif media_type == "video":
                            media_group.append(InputMediaVideo(media=file_id, caption=caption, parse_mode=parse_mode if caption else None))
                    
                    if len(media_group) == 1:
                        # Одно медиа
                        if media_group[0].media.type == "photo":
                            message_data = {
                                "type": "photo",
                                "photo": media_group[0].media.file_id,
                                "caption": publication_text
                            }
                            await send_publication_with_rate_limit(fake_context, chat_id, message_data)
                        else:
                            message_data = {
                                "type": "video",
                                "video": media_group[0].media.file_id,
                                "caption": publication_text
                            }
                            await send_publication_with_rate_limit(fake_context, chat_id, message_data)
                    else:
                        message_data = {
                            "type": "media_group",
                            "media": media_group,
                            "caption": publication_text if len(media_group) < len(media_files) else None
                        }
                        await send_publication_with_rate_limit(fake_context, chat_id, message_data)
                else:
                    message_data = {
                        "type": "text",
                        "text": publication_text
                    }
                    await send_publication_with_rate_limit(fake_context, chat_id, message_data)
                
                await increment_chat_publications(chat_id)
                published_count += 1
                success = True
                
                await log_action("AUTOPUBLISH_OBJECT_PUBLISHED", int(user_id), user_info.get("username"), 
                               f"Chat: {chat_id}, Object: {object_id}")
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                error_type = type(e).__name__
                
                # Если это сетевая ошибка, ждем перед повтором
                if "NetworkError" in error_type or "ConnectError" in error_type or "getaddrinfo" in error_msg:
                    if retry_count < max_retries:
                        wait_time = retry_count * 5  # Увеличиваем время ожидания с каждой попыткой
                        await log_action("AUTOPUBLISH_NETWORK_RETRY", int(user_id), user_info.get("username"), 
                                       f"Chat: {chat_id}, Retry: {retry_count}/{max_retries}, Wait: {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                
                await log_action("AUTOPUBLISH_PUBLICATION_ERROR", int(user_id), user_info.get("username"), 
                               f"Chat: {chat_id}, Error: {error_msg}, Type: {error_type}, Retries: {retry_count}")
                break  # Выходим из цикла повторных попыток
    
    # Обновление объекта
    now = get_moscow_time()
    publication_datetime = format_moscow_datetime(now)
    await update_object(object_id, {
        "status": "опубликовано",
        "publication_date": publication_datetime,
        "target_chats": target_chats,
        "phone_number": phone
    })
    
    # Обновление статистики пользователя
    if user_info:
        user_info["total_publications"] = user_info.get("total_publications", 0) + 1
        await save_user(user_id, user_info)
    
    await log_action("AUTOPUBLISH_COMPLETE", int(user_id), user_info.get("username"), 
                   f"Object: {object_id}, Published to {published_count} chats")
    
    # Отправка уведомления пользователю об успешной публикации
    if published_count > 0:
        try:
            # Получаем названия чатов
            chats = await get_chats()
            chat_names = []
            for chat_id in target_chats:
                chat_data = chats.get(chat_id, {})
                chat_title = chat_data.get('title', f'Чат {chat_id}')
                chat_names.append(chat_title)
            
            # Формируем текст уведомления
            price = obj.get('price', 0)
            districts = obj.get('districts', [])
            districts_str = ', '.join(districts) if districts else 'Не указано'
            
            # Форматируем дату и время публикации
            pub_date = parse_moscow_datetime(publication_datetime, "%Y-%m-%d %H:%M:%S")
            formatted_datetime = format_moscow_datetime(pub_date, "%d.%m.%Y %H:%M")
            
            # Формируем список чатов
            chats_str = ', '.join(chat_names) if chat_names else 'Не указано'
            
            notification_text = (
                f"✅ <b>Объекты успешно опубликованы</b>\n\n"
                f"💰 <b>Цена:</b> {price} тыс. руб.\n"
                f"📍 <b>Районы:</b> {districts_str}\n"
                f"📅 <b>Дата и время публикации:</b> {formatted_datetime}\n"
                f"💬 <b>Чаты публикации:</b> {chats_str}"
            )
            
            # Отправляем уведомление пользователю
            await app.bot.send_message(
                chat_id=int(user_id),
                text=notification_text,
                parse_mode=ParseMode.HTML
            )
            
            await log_action("AUTOPUBLISH_NOTIFICATION_SENT", int(user_id), user_info.get("username"), 
                           f"Object: {object_id}")
        except Exception as e:
            await log_action("AUTOPUBLISH_NOTIFICATION_ERROR", int(user_id), user_info.get("username"), 
                           f"Object: {object_id}, Error: {str(e)}")

# ==================== НАСТРОЙКА ЛОГГЕРА ====================
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Настройка расширенного логирования"""
    # Создаем основного логгера
    logger = logging.getLogger('telegram_bot')
    logger.setLevel(logging.DEBUG)
    
    # Форматтеры
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-30s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '\n' + '='*80 + '\n'
        '[%(asctime)s] | %(levelname)s | %(name)s | %(message)s\n'
        + '='*80 + '\n',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольный обработчик (только важные сообщения)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Файловый обработчик для детального лога (ротация по 10МБ, 5 файлов)
    file_handler = RotatingFileHandler(
        'bot_detailed.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Файловый обработчик для ошибок
    error_handler = RotatingFileHandler(
        'bot_errors.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(detailed_formatter)
    
    # Старый файл для совместимости
    old_file_handler = logging.FileHandler('bot.log', encoding='utf-8')
    old_file_handler.setLevel(logging.INFO)
    old_file_handler.setFormatter(simple_formatter)
    
    # Очищаем существующие обработчики
    if logger.handlers:
        logger.handlers.clear()
    
    # Добавляем обработчики
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(old_file_handler)
    
    # Устанавливаем уровень для библиотек
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    return logger

# Инициализация логирования
logger = setup_logging()

# Отключаем логирование от библиотек
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)

# ==================== ФУНКЦИИ ЛОГИРОВАНИЯ ====================
async def log_action(action: str, user_id: int = None, username: str = None, details: str = ""):
    """Логирование действия через logger и в log.txt"""
    try:
        timestamp = format_moscow_datetime()
        username_str = f"@{username}" if username else "N/A"
        user_id_str = str(user_id) if user_id else "N/A"
        
        log_message = f"Действие: {action} | UserID: {user_id_str} | Username: {username_str} | Детали: {details}"
        
        # Логирование через logger
        logger.info(log_message)
        
        # Дополнительное логирование в старый формат для совместимости
        log_entry = f"[{timestamp}] | Действие: {action} | UserID: {user_id_str} | Username: {username_str} | Детали: {details}\n"
        async with aiofiles.open("log.txt", 'a', encoding='utf-8') as f:
            await f.write(log_entry)
    except Exception as e:
        logger.error(f"Error logging action: {e}", exc_info=True)


async def log_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик для логирования всех callback_query"""
    if update.callback_query:
        query = update.callback_query
        user = update.effective_user
        callback_data = query.data
        message_id = query.message.message_id if query.message else "N/A"
        chat_id = query.message.chat_id if query.message else "N/A"
        
        await log_action(
            "CALLBACK_QUERY_RECEIVED",
            user.id if user else None,
            user.username if user else None,
            f"Callback: {callback_data}, Message ID: {message_id}, Chat ID: {chat_id}, From: {query.from_user.id if query.from_user else 'N/A'}"
        )
        
        print(f"\n{'#'*80}")
        print(f"CALLBACK QUERY DETAILS:")
        print(f"  Data: {callback_data}")
        print(f"  User: {user.id if user else 'N/A'} (@{user.username if user and user.username else 'N/A'})")
        print(f"  Message ID: {message_id}")
        print(f"  Chat ID: {chat_id}")
        print(f"  Time: {format_moscow_datetime()}")
        print(f"{'#'*80}\n")

async def log_statistics(stats_data: dict):
    """Логирование статистики в statistics_log.txt"""
    try:
        timestamp = format_moscow_datetime()
        log_entry = f"\n[{timestamp}]\n"
        log_entry += f"Новые пользователи: {stats_data.get('new_users', {})}\n"
        log_entry += f"Активные пользователи: {stats_data.get('active_users', {})}\n"
        log_entry += f"Публикации: {stats_data.get('publications', {})}\n"
        log_entry += f"Распределение по чатам: {stats_data.get('publications_by_chat', {})}\n"
        log_entry += "-" * 50 + "\n"
        
        async with aiofiles.open("statistics_log.txt", 'a', encoding='utf-8') as f:
            await f.write(log_entry)
    except Exception as e:
        print(f"Error logging statistics: {e}")


# FSM состояния для пользователей
OBJECT_WAITING_ROOMS, OBJECT_WAITING_DISTRICT, OBJECT_WAITING_PRICE, \
OBJECT_PREVIEW_MENU, OBJECT_WAITING_ADD_DISTRICT, OBJECT_WAITING_MEDIA, \
OBJECT_WAITING_AREA, OBJECT_WAITING_FLOOR, OBJECT_WAITING_COMMENT, OBJECT_WAITING_RENOVATION, \
OBJECT_WAITING_ADDRESS, OBJECT_WAITING_CONTACTS, OBJECT_WAITING_NAME, \
OBJECT_WAITING_EDIT_ROOMS, OBJECT_WAITING_EDIT_DISTRICT, OBJECT_WAITING_EDIT_PRICE = range(16)

# FSM состояния для админа
ADMIN_WAITING_CHAT_ID, ADMIN_WAITING_CHAT_TITLE, ADMIN_WAITING_CHAT_TYPE, \
ADMIN_WAITING_CHAT_PARAMS, ADMIN_EDITING_DISTRICT, ADMIN_EDITING_PRICE_RANGE, \
ADMIN_EDITING_ROLE, ADMIN_EDITING_HASHTAG_SUFFIX = range(6, 14)

# Состояния настроек
SETTINGS_WAITING_PHONE = 18
SETTINGS_WAITING_NAME = 19

# Временное хранилище для данных пользователей (FSM)
user_data: Dict[int, Dict] = {}


async def is_private_chat(update: Update) -> bool:
    """Проверка, что сообщение пришло из личного чата"""
    if update.message:
        return update.message.chat.type == "private"
    elif update.callback_query and update.callback_query.message:
        return update.callback_query.message.chat.type == "private"
    return False

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверка подписки пользователя на канал и чат"""
    user = update.effective_user
    check_enabled = await get_subscription_check_flag()
    
    if not check_enabled:
        return True
    
    try:
        member_channel = await context.bot.get_chat_member(CHANNEL_ID, user.id)
        member_chat = await context.bot.get_chat_member(AUTHORS_CHAT_ID, user.id)
        
        return (member_channel.status in ['member', 'administrator', 'creator'] and
                member_chat.status in ['member', 'administrator', 'creator'])
    except Exception as e:
        await log_action("SUBSCRIPTION_CHECK_ERROR", user.id, user.username, str(e))
        return False


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    # Проверка, что сообщение из личного чата
    if not await is_private_chat(update):
        return
    
    user = update.effective_user
    
    # Очистка состояния FSM
    if user.id in user_data:
        del user_data[user.id]
    
    await log_action("START_COMMAND", user.id, user.username)
    
    # Проверка на администратора
    if user.id == ADMIN_ID:
        await show_admin_panel(update, context)
    else:
        # Проверка подписки для обычных пользователей
        check_enabled = await get_subscription_check_flag()
        
        if check_enabled:
            is_subscribed = await check_subscription(update, context)
            
            if not is_subscribed:
                # Устанавливаем роль broke, если пользователь не подписан
                user_info = await get_user(str(user.id))
                if user_info:
                    if user_info.get("role") == ROLE_START:
                        await set_user_role(str(user.id), ROLE_BROKE)
                await show_subscription_required(update, context)
                return
        
        # Обновление информации о пользователе
        await update_user_activity(user.id, user.username)
        user_info = await get_user(str(user.id))
        if user_info:
            # Если пользователь прошел проверку подписки и был broke, меняем на beginner
            if user_info.get("role") == ROLE_BROKE:
                user_info["role"] = ROLE_BEGINNER
            await save_user(str(user.id), {
                **user_info,
                "subscription_checked": True
            })
        
        await show_main_menu(update, context)


async def show_subscription_required(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать сообщение о необходимости подписки"""
    keyboard = [
        [InlineKeyboardButton(BUTTON_SUBSCRIBE, url=f"https://t.me/c/{str(CHANNEL_ID)[4:]}/1")],
        [InlineKeyboardButton(BUTTON_CHECK_SUBSCRIPTION, callback_data="check_subscription")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        SUBSCRIPTION_REQUIRED,
        reply_markup=reply_markup
    )


async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки проверки подписки"""
    query = update.callback_query
    await query.answer()
    
    is_subscribed = await check_subscription(update, context)
    
    if is_subscribed:
        user = update.effective_user
        await update_user_activity(user.id, user.username)
        user_info = await get_user(str(user.id))
        if user_info:
            await save_user(str(user.id), {
                **user_info,
                "subscription_checked": True
            })
        await show_main_menu_from_callback(update, context)
    else:
        await query.edit_message_text(
            "Вы еще не подписаны. Пожалуйста, подпишитесь на канал и чат."
        )


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать панель администратора"""
    check_enabled = await get_subscription_check_flag()
    check_status = "Включена" if check_enabled else "Выключена"
    
    keyboard = [
        [InlineKeyboardButton("Добавить чат", callback_data="admin_add_chat")],
        [InlineKeyboardButton("Список чатов", callback_data="admin_chat_list")],
        [InlineKeyboardButton("Настройки районов", callback_data="admin_districts_config")],
        [InlineKeyboardButton("Настройки цен", callback_data="admin_price_config")],
        [InlineKeyboardButton("Настройки комнат", callback_data="admin_rooms_config")],
        [InlineKeyboardButton("Хэштеги", callback_data="admin_hashtags")],
        [InlineKeyboardButton("Статистика", callback_data="admin_statistics")],
        [InlineKeyboardButton("Управление ролями", callback_data="admin_manage_roles")],
        [InlineKeyboardButton(f"Вкл/Выкл проверку подписки ({check_status})", 
                             callback_data="admin_toggle_subscription_check")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"<b>{ADMIN_PANEL_TEXT}</b>\n\nПроверка подписки: {check_status}"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать главное меню пользователя"""
    user = update.effective_user
    await log_action("MAIN_MENU_SHOWN", user.id, user.username)
    
    # Получаем роль пользователя
    user_role = await get_user_role(str(user.id))
    role_display_names = {
        ROLE_START: "Старт",
        ROLE_BROKE: "Брокер",
        ROLE_BEGINNER: "Начинающий",
        ROLE_FREE: "Бесплатный",
        ROLE_FREEPREMIUM: "Бесплатный Премиум",
        ROLE_PREMIUM: "Премиум",
        ROLE_PROTIME: "Pro Time"
    }
    role_display = role_display_names.get(user_role, user_role)
    
    keyboard = [
        [InlineKeyboardButton("Добавить объект", callback_data="add_object")],
        [InlineKeyboardButton("Мои объекты", callback_data="my_objects")],
        [InlineKeyboardButton("Настройки автопубликации", callback_data="auto_publish_settings")],
        [InlineKeyboardButton("Настройки", callback_data="settings")],
        [
            InlineKeyboardButton("📁 Папка со всеми чатами", url="https://t.me/addlist/QDGm9RwOldE4YzM6"),
            InlineKeyboardButton("💬 Связь с админом", url="https://t.me/bochkarev_t")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"{WELCOME_TEXT}\n\n<b>Ваша роль:</b> <b>{role_display}</b>"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    elif update.callback_query:
        # Используем safe_edit_message для безопасного редактирования
        await safe_edit_message(update.callback_query, text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        # Если нет ни message, ни callback_query, отправляем новое сообщение
        if hasattr(update, 'effective_message') and update.effective_message:
            await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def show_main_menu_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать главное меню из callback"""
    query = update.callback_query
    await query.answer()
    await show_main_menu(update, context)


# ==================== Обработка добавления объекта ====================

async def add_object_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса добавления объекта"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # ИСПРАВЛЕНО: Проверяем и очищаем предыдущее состояние ConversationHandler
    conv_state = context.user_data.get('_conversation_state', 'N/A')
    logger.info(f"ADD_OBJECT_START - User: {user.id}, Current conv state: {conv_state}")
    
    # Если ConversationHandler активен, очищаем его состояние
    if conv_state != 'N/A':
        logger.info(f"ADD_OBJECT_START - Clearing previous conversation state: {conv_state}")
        # Очищаем состояние ConversationHandler
        context.user_data.pop('_conversation_state', None)
        context.user_data.pop('_conversation_name', None)
        # Очищаем все ключи, связанные с ConversationHandler
        conv_keys = [k for k in list(context.user_data.keys()) if k.startswith('_conversation')]
        for key in conv_keys:
            context.user_data.pop(key, None)
        logger.info(f"ADD_OBJECT_START - Cleared conversation keys: {conv_keys}")
    
    # Очищаем старые данные пользователя, если они есть
    if user.id in user_data:
        old_object_id = user_data[user.id].get("object_id", "N/A")
        logger.info(f"ADD_OBJECT_START - Clearing old user_data, old object_id: {old_object_id}")
        # Если есть незавершенный объект, удаляем его
        if old_object_id != "N/A" and old_object_id:
            try:
                await delete_object(old_object_id)
                logger.info(f"ADD_OBJECT_START - Deleted old object: {old_object_id}")
            except Exception as e:
                logger.error(f"ADD_OBJECT_START - Error deleting old object {old_object_id}: {e}")
        user_data.pop(user.id, None)
    
    await log_action("ADD_OBJECT_BUTTON_CLICKED", user.id, user.username, "Starting object creation")
    
    object_id = await create_object(user.id)
    
    # Инициализация временных данных
    user_data[user.id] = {
        "object_id": object_id,
        "districts": []
    }
    
    # Если пользователь был start или broke, меняем на beginner после создания объекта
    user_info = await get_user(str(user.id))
    if user_info:
        current_role = user_info.get("role", ROLE_START)
        if current_role in [ROLE_START, ROLE_BROKE]:
            await set_user_role(str(user.id), ROLE_BEGINNER)
    
    await log_action("OBJECT_CREATED", user.id, user.username, f"Object ID: {object_id}")
    
    # Шаг 1: Выбор типа комнат (кнопки в одну строку по возможности)
    rooms = await get_rooms_config()
    # Разбиваем на строки по 3 кнопки
    keyboard = []
    row = []
    for i, room in enumerate(rooms):
        row.append(InlineKeyboardButton(room, callback_data=f"rooms_{room}"))
        if len(row) == 3 or i == len(rooms) - 1:
            keyboard.append(row)
            row = []
    # Добавляем кнопку "Главное меню"
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(ADD_OBJECT_ROOMS_QUESTION, reply_markup=reply_markup)

    # Явно фиксируем состояние диалога, чтобы ConversationHandler не терял его
    context.user_data["_conversation_state"] = OBJECT_WAITING_ROOMS
    context.user_data["_conversation_name"] = "add_object_handler"
    return OBJECT_WAITING_ROOMS


async def object_rooms_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора типа комнат"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    rooms_type = query.data.replace("rooms_", "")
    await log_action("ROOMS_SELECTED", user.id, user.username, f"Rooms: {rooms_type}")
    
    # Сохранение типа комнат
    object_id = user_data[user.id]["object_id"]
    await update_object(object_id, {"rooms_type": rooms_type})
    
    await log_action("OBJECT_ROOMS_SELECTED", user.id, user.username, f"Rooms: {rooms_type}")
    
    # Шаг 2: Выбор районов
    districts_config = await get_districts_config()
    districts = list(districts_config.keys())
    
    if not districts:
        # Если районов нет, пропускаем этот шаг
        await query.edit_message_text(ADD_OBJECT_PRICE_QUESTION)
        return OBJECT_WAITING_PRICE
    
    keyboard = [[InlineKeyboardButton(district, callback_data=f"district_{district}")] 
                for district in districts]
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(ADD_OBJECT_DISTRICT_QUESTION, reply_markup=reply_markup)
    return OBJECT_WAITING_DISTRICT


async def object_district_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора района"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    district = query.data.replace("district_", "")
    
    logger.info(f"object_district_selected called - User: {user.id}, District: {district}")
    logger.info(f"OBJECT_DISTRICT_SELECTED_DETAILS - User: {user.id}, District: {district}, User data exists: {user.id in user_data}")
    await log_action("OBJECT_DISTRICT_SELECTED_DETAILS", user.id, user.username, 
                    f"District: {district}, User data: {user.id in user_data}")
    
    # Проверяем наличие user_data
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        logger.error(f"NO_USER_DATA_FOR_DISTRICT - User: {user.id}, user_data: {user_data.get(user.id, {})}")
        await query.edit_message_text("Ошибка: данные объекта не найдены. Начните заново.")
        return ConversationHandler.END
    
    # Добавление района
    if "districts" not in user_data[user.id]:
        user_data[user.id]["districts"] = []
    if district not in user_data[user.id]["districts"]:
        user_data[user.id]["districts"].append(district)
    
    # Обновление объекта
    object_id = user_data[user.id]["object_id"]
    await update_object(object_id, {"districts": user_data[user.id]["districts"]})
    
    logger.info(f"OBJECT_UPDATED_WITH_DISTRICT - Object: {object_id}, Districts: {user_data[user.id]['districts']}")
    logger.info(f"OBJECT_DISTRICT_SELECTED - User: {user.id}, District: {district}, Object: {object_id}")
    await log_action("OBJECT_DISTRICT_ADDED_FULL", user.id, user.username, 
                    f"Object: {object_id}, District: {district}")
    
    # Переход к цене (без вопроса о добавлении еще района)
    logger.info(f"SENDING_PRICE_QUESTION - User: {user.id}, Question: {ADD_OBJECT_PRICE_QUESTION}")
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(ADD_OBJECT_PRICE_QUESTION, reply_markup=reply_markup)
        logger.info(f"PRICE_QUESTION_SENT_SUCCESS - User: {user.id}")
        await log_action("PRICE_QUESTION_SENT", user.id, user.username, "Success")
    except Exception as e:
        logger.error(f"ERROR_SENDING_PRICE_QUESTION - User: {user.id}, Error: {str(e)}")
        try:
            await query.message.reply_text(ADD_OBJECT_PRICE_QUESTION, reply_markup=reply_markup)
            logger.info(f"PRICE_QUESTION_SENT_FALLBACK - User: {user.id}")
            await log_action("PRICE_QUESTION_SENT_FALLBACK", user.id, user.username, f"Error: {str(e)}")
        except Exception as e2:
            logger.error(f"ERROR_SENDING_PRICE_QUESTION_FALLBACK - User: {user.id}, Error: {str(e2)}")
            await log_action("PRICE_QUESTION_SENT_FAILED", user.id, user.username, f"Error: {str(e2)}")
    
    logger.info(f"RETURNING_OBJECT_WAITING_PRICE - User: {user.id}, State: {OBJECT_WAITING_PRICE}")
    return OBJECT_WAITING_PRICE


async def object_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода цены"""
    user = update.effective_user
    logger.info(f"OBJECT_PRICE_INPUT_CALLED - User: {user.id}, Text: {update.message.text}, User data exists: {user.id in user_data}")
    await log_action("PRICE_INPUT_RECEIVED_DETAILS", user.id, user.username, 
                    f"Input: {update.message.text}, User data exists: {user.id in user_data}")
    
    if user.id not in user_data:
        logger.error(f"NO_USER_DATA_FOR_PRICE - User: {user.id}")
        await update.message.reply_text("Ошибка: данные объекта не найдены. Начните заново.")
        return ConversationHandler.END
    
    if "object_id" not in user_data[user.id]:
        logger.error(f"NO_OBJECT_ID_FOR_PRICE - User: {user.id}, user_data keys: {list(user_data[user.id].keys())}")
        await update.message.reply_text("Ошибка: ID объекта не найден. Начните заново.")
        return ConversationHandler.END
    
    try:
        price = float(update.message.text.replace(",", "."))
        if price <= 0:
            raise ValueError
        
        # Сохранение цены
        object_id = user_data[user.id]["object_id"]
        await update_object(object_id, {"price": price})
        
        logger.info(f"PRICE_SAVED - Object: {object_id}, Price: {price}")
        await log_action("OBJECT_PRICE_SET_DETAILS", user.id, user.username, 
                        f"Object: {object_id}, Price: {price}")
        
        # Переход к обязательному вопросу о площади
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Введите площадь в м²:", reply_markup=reply_markup)
        logger.info(f"ASKING_FOR_AREA - User: {user.id}, Returning state: {OBJECT_WAITING_AREA}")
        return OBJECT_WAITING_AREA
        
    except ValueError:
        logger.warning(f"INVALID_PRICE_INPUT - User: {user.id}, Input: {update.message.text}")
        await update.message.reply_text(ERROR_INVALID_PRICE)
        return OBJECT_WAITING_PRICE


# Старые функции удалены - теперь используется новая логика с меню расширенных настроек


async def show_object_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, obj: Dict, user_info: Dict = None):
    """Показать предпросмотр объекта"""
    # Формирование текста
    text = f"<b>{OBJECT_PREVIEW_TITLE}</b>\n\n"
    text += f"<b>{OBJECT_PREVIEW_ROOMS}:</b> {obj.get('rooms_type', 'Не указано')}\n"
    text += f"<b>{OBJECT_PREVIEW_PRICE}:</b> {obj.get('price', 0)} тыс. руб.\n"
    
    districts = obj.get('districts', [])
    if districts:
        text += f"<b>{OBJECT_PREVIEW_DISTRICTS}:</b> {', '.join(districts)}\n"
    
    caption = obj.get('caption', '')
    if caption:
        text += f"\n<b>{OBJECT_PREVIEW_CAPTION}:</b>\n{caption}\n"
    
    phone = obj.get('phone_number', '')
    if not phone and user_info:
        phone = user_info.get('phone_number', '')
    if phone:
        text += f"\n<b>{OBJECT_PREVIEW_PHONE}:</b> {phone}"
    
    # Кнопки
    keyboard = [
        [InlineKeyboardButton(BUTTON_PUBLISH, callback_data="publish_object")],
        [InlineKeyboardButton(BUTTON_EDIT, callback_data="edit_object")],
        [InlineKeyboardButton(BUTTON_CANCEL, callback_data="cancel_object")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Определяем, откуда вызвана функция (message или callback_query)
    message = update.message if update.message else update.callback_query.message
    
    # Отправка медиа, если есть
    media_files = obj.get('media_files', [])
    if media_files:
        try:
            media_group = []
            for media in media_files[:10]:  # Telegram позволяет до 10 медиа в группе
                if media['type'] == 'photo':
                    # Для первого медиа добавляем caption, для остальных - None
                    media_group.append(InputMediaPhoto(media['file_id'], caption=text if len(media_group) == 0 else None))
                elif media['type'] == 'video':
                    media_group.append(InputMediaVideo(media['file_id'], caption=text if len(media_group) == 0 else None))
            
            if len(media_group) == 1:
                # Одно медиа - отправляем с текстом
                # Проверяем тип через isinstance, так как media_type не существует
                if isinstance(media_group[0], InputMediaPhoto):
                    sent_message = await message.reply_photo(
                        photo=media_group[0].media,
                        caption=text,
                        reply_markup=reply_markup
                    )
                else:
                    sent_message = await message.reply_video(
                        video=media_group[0].media,
                        caption=text,
                        reply_markup=reply_markup
                    )
            else:
                # Несколько медиа - отправляем группу, затем текст с кнопками
                await message.reply_media_group(media=media_group)
                await message.reply_text(text, reply_markup=reply_markup)
        except Exception as e:
            await log_action("PREVIEW_MEDIA_ERROR", update.effective_user.id, 
                                   update.effective_user.username, str(e))
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
            else:
                await message.reply_text(text, reply_markup=reply_markup)
    else:
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await message.reply_text(text, reply_markup=reply_markup)


async def show_object_preview_with_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, obj: Dict, user_info: Dict = None):
    """Показать предпросмотр объекта с меню расширенных настроек"""
    # Получаем user из update
    user = update.effective_user
    
    # Проверяем, не отправляется ли уже превью (защита от множественных вызовов)
    preview_lock_key = f"preview_sending_{user.id}"
    if preview_lock_key in user_data.get(user.id, {}):
        await log_action("PREVIEW_SKIPPED_DUPLICATE", user.id, user.username, "Preview already sending, skipping")
        return  # Уже отправляется превью, пропускаем
    
    # Устанавливаем флаг, что превью отправляется
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id][preview_lock_key] = True
    
    await log_action("PREVIEW_START", user.id, user.username, f"Object: {obj.get('rooms_type', 'N/A')}, Media count: {len(obj.get('media_files', []))}")
    
    # Получаем user_info если не передан
    if not user_info:
        user_info = await get_user(str(user.id))
    
    # Формирование текста предпросмотра в новом формате (без футера для превью редактирования)
    text = await format_publication_text(obj, user_info, is_preview=True)
    
    # Медиа информация
    media_count = len(obj.get('media_files', []))
    if media_count > 0:
        text += f"\n<b>Медиа:</b> {media_count} файл(ов)\n"
    
    # Получаем object_id из user_data
    object_id = None
    if user.id in user_data and "object_id" in user_data[user.id]:
        object_id = user_data[user.id]["object_id"]
    
    # Получаем статус автопубликации для объекта
    autopublish_enabled = False
    if object_id:
        autopublish_enabled = await get_object_autopublish_enabled(object_id)
    autopublish_text = "Автопубликация✅" if autopublish_enabled else "Автопубликация❌"
    
    # Меню расширенных настроек (новый порядок)
    keyboard = [
        [InlineKeyboardButton("Изменить стоимость", callback_data="edit_price_menu")],
        [InlineKeyboardButton("Выбрать фото", callback_data="add_media_menu")],
        [InlineKeyboardButton("Изменить комментарий", callback_data="set_comment")],
        [
            InlineKeyboardButton("Добавить еще район", callback_data="add_more_district_menu"),
            InlineKeyboardButton("Изменить район", callback_data="edit_district_menu")
        ],
        [
            InlineKeyboardButton("Площадь", callback_data="set_area"),
            InlineKeyboardButton("Этаж", callback_data="set_floor")
        ],
        [
            InlineKeyboardButton("Изменить комнаты", callback_data="edit_rooms_menu"),
            InlineKeyboardButton("Состояние ремонта", callback_data="set_renovation")
        ],
        [
            InlineKeyboardButton("Адрес", callback_data="set_address"),
            InlineKeyboardButton("Контакты", callback_data="set_contacts")
        ],
        [InlineKeyboardButton("Опубликовать сейчас", callback_data="publish_immediate_current")],
        [
            InlineKeyboardButton("Выбрать время", callback_data="publish_schedule_menu"),
        ],
        [
            InlineKeyboardButton(autopublish_text, callback_data="toggle_autopublish"),
            InlineKeyboardButton("Удалить", callback_data="delete_current_object")
        ],
        [
            InlineKeyboardButton("Мои объекты", callback_data="my_objects"),
            InlineKeyboardButton("Настройки автопубликации", callback_data="auto_publish_settings")
        ],
        [InlineKeyboardButton("Главное меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Определяем, откуда вызвана функция
    if update.message:
        message = update.message
    elif update.callback_query:
        message = update.callback_query.message
    else:
        await log_action("PREVIEW_ERROR_NO_MESSAGE", user.id, user.username, "No message found in update")
        return
    
    # Удаляем предыдущие превью и меню, если они есть
    await delete_preview_and_menu(context, user.id)
    
    # Если это callback_query, удаляем также сообщение с кнопкой (но только если это не меню)
    if update.callback_query:
        # Проверяем, не является ли это сообщение меню (чтобы не удалить меню, которое мы только что показали)
        menu_id = user_data.get(user.id, {}).get("menu_message_id")
        if menu_id != update.callback_query.message.message_id:
            try:
                await update.callback_query.message.delete()
            except:
                pass
    
    # Отправка медиа, если есть (БЕЗ кнопок)
    media_files = obj.get('media_files', [])
    preview_message = None
    
    try:
        if media_files:
            try:
                media_group = []
                for media in media_files[:10]:
                    if media['type'] == 'photo':
                        # Добавляем caption только к первому медиа
                        media_group.append(InputMediaPhoto(
                            media['file_id'], 
                            caption=text if len(media_group) == 0 else None
                        ))
                    elif media['type'] == 'video':
                        # Добавляем caption только к первому медиа
                        media_group.append(InputMediaVideo(
                            media['file_id'], 
                            caption=text if len(media_group) == 0 else None
                        ))
                
                if len(media_group) == 1:
                    # Одно медиа - отправляем с текстом БЕЗ кнопок
                    if isinstance(media_group[0], InputMediaPhoto):
                        preview_message = await message.reply_photo(
                            photo=media_group[0].media,
                            caption=text
                        )
                    else:
                        preview_message = await message.reply_video(
                            video=media_group[0].media,
                            caption=text
                        )
                else:
                    # Несколько медиа - отправляем группу с caption на первом медиа
                    # Caption уже добавлен к первому медиа в media_group с parse_mode=HTML
                    sent_messages = await message.reply_media_group(media=media_group)
                    # Используем первое сообщение из группы как preview_message для отслеживания
                    if sent_messages:
                        preview_message = sent_messages[0]
                    else:
                        # Если не получили сообщения, создаем фиктивное сообщение для отслеживания
                        preview_message = None
            except Exception as e:
                await log_action("PREVIEW_MEDIA_ERROR", update.effective_user.id, 
                                       update.effective_user.username, str(e))
                preview_message = await message.reply_text(text)
        else:
            # Нет медиа - просто текст БЕЗ кнопок
            preview_message = await message.reply_text(text)
        
        # Отправляем меню отдельным сообщением ПОСЛЕ превью
        menu_text = "Выберите действие:"
        menu_message = await message.reply_text(menu_text, reply_markup=reply_markup)
        
        # Сохраняем ID сообщений превью и меню во временных данных для возможности удаления
        if preview_message:
            user_data[user.id]["preview_message_id"] = preview_message.message_id
        user_data[user.id]["menu_message_id"] = menu_message.message_id
        user_data[user.id]["preview_chat_id"] = message.chat_id
    except Exception as e:
        await log_action("PREVIEW_SEND_ERROR", user.id, user.username, f"Error: {str(e)}")
    finally:
        # Снимаем флаг отправки превью в любом случае
        if user.id in user_data:
            preview_lock_key = f"preview_sending_{user.id}"
            user_data[user.id].pop(preview_lock_key, None)


# ==================== Обработчики меню расширенных настроек ====================

async def add_more_district_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавить еще район из меню"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await delete_preview_and_menu(context, user.id)
    
    districts_config = await get_districts_config()
    districts = list(districts_config.keys())
    
    if not districts:
        await query.message.reply_text("Нет доступных районов")
        return
    
    keyboard = [[InlineKeyboardButton(district, callback_data=f"district_{district}")] 
                for district in districts]
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_preview")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(ADD_OBJECT_DISTRICT_QUESTION, reply_markup=reply_markup)
    return OBJECT_WAITING_ADD_DISTRICT


async def add_media_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор медиа из меню (удаляет предыдущие и спрашивает новые)"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    await log_action("ADD_MEDIA_MENU_CLICKED", user.id, user.username, f"Callback data: {query.data}, Message ID: {query.message.message_id if query.message else 'N/A'}")
    
    # Проверяем наличие object_id
    if user.id not in user_data:
        await log_action("ADD_MEDIA_MENU_ERROR_NO_USER_DATA", user.id, user.username, "user_data not found")
        await query.answer("Ошибка: данные объекта не найдены.", show_alert=True)
        return OBJECT_PREVIEW_MENU
    
    if "object_id" not in user_data[user.id]:
        await log_action("ADD_MEDIA_MENU_ERROR_NO_OBJECT_ID", user.id, user.username, f"user_data keys: {list(user_data[user.id].keys())}")
        await query.answer("Ошибка: данные объекта не найдены.", show_alert=True)
        return OBJECT_PREVIEW_MENU
    
    object_id = user_data[user.id]["object_id"]
    await log_action("ADD_MEDIA_MENU_OBJECT_FOUND", user.id, user.username, f"Object: {object_id}")
    
    # Получаем текущий объект для логирования
    obj = await get_object(object_id)
    current_media_count = len(obj.get("media_files", [])) if obj else 0
    await log_action("ADD_MEDIA_MENU_CURRENT_MEDIA", user.id, user.username, f"Object: {object_id}, Current media count: {current_media_count}")
    
    # Удаляем все предыдущие медиа (даже если их нет)
    await update_object(object_id, {"media_files": []})
    await log_action("OBJECT_MEDIA_CLEARED", user.id, user.username, f"Object: {object_id}, Previous count: {current_media_count}")
    
    # Удаляем превью и меню
    await log_action("ADD_MEDIA_MENU_DELETING_PREVIEW", user.id, user.username, f"Object: {object_id}")
    await delete_preview_and_menu(context, user.id)
    
    await log_action("ADD_MEDIA_MENU_ASKING_FOR_MEDIA", user.id, user.username, f"Object: {object_id}")
    await query.message.reply_text(ADD_OBJECT_MEDIA_QUESTION + "\n\nВведите /skip чтобы вернуться к меню.")
    return OBJECT_WAITING_MEDIA


async def safe_edit_message(query, text: str, reply_markup=None, parse_mode=None):
    """Безопасное редактирование сообщения (работает с фото и текстом)"""
    try:
        # Проверяем, есть ли в сообщении фото или видео
        if query.message.photo or query.message.video:
            # Если есть медиа, редактируем caption
            try:
                await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
                return
            except Exception as e:
                # Если не получилось редактировать caption, отправляем новое сообщение
                await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
                return
        
        # Если нет медиа, редактируем текст
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        # Если редактирование не удалось, отправляем новое сообщение
        try:
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e2:
            # Если и это не сработало, логируем ошибку
            await log_action("SAFE_EDIT_MESSAGE_ERROR", None, None, f"Error: {str(e2)}")

async def delete_preview_and_menu(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Удалить превью и меню объекта"""
    if user_id in user_data:
        chat_id = user_data[user_id].get("preview_chat_id")
        preview_id = user_data[user_id].get("preview_message_id")
        menu_id = user_data[user_id].get("menu_message_id")
        
        if chat_id and preview_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=preview_id)
            except:
                pass
            # Очищаем ID после удаления
            user_data[user_id].pop("preview_message_id", None)
        
        if chat_id and menu_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=menu_id)
            except:
                pass
            # Очищаем ID после удаления
            user_data[user_id].pop("menu_message_id", None)

async def set_area_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить площадь"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await delete_preview_and_menu(context, user.id)
    
    # Отправляем вопрос с кнопками
    keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Введите площадь в м²:", reply_markup=reply_markup)
    return OBJECT_WAITING_AREA


async def set_floor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить этаж"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await delete_preview_and_menu(context, user.id)
    
    # Отправляем вопрос с кнопками
    keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Введите этаж:", reply_markup=reply_markup)
    return OBJECT_WAITING_FLOOR


async def set_comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить комментарий после фото"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await delete_preview_and_menu(context, user.id)
    
    # Отправляем вопрос с кнопками
    keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Опишите квартиру и условия покупки: обременения и тп", reply_markup=reply_markup)
    return OBJECT_WAITING_COMMENT


async def set_renovation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить состояние ремонта"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await delete_preview_and_menu(context, user.id)
    
    renovations = ["Черновая", "ПЧО", "Ремонт требует освежения", "Хороший ремонт", "Инстаграмный"]
    keyboard = [[InlineKeyboardButton(ren, callback_data=f"renovation_{ren}")] for ren in renovations]
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_preview")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text("Выберите состояние ремонта:", reply_markup=reply_markup)
    return OBJECT_WAITING_RENOVATION


async def set_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить адрес"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await delete_preview_and_menu(context, user.id)
    
    # Отправляем вопрос с кнопками
    keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Введите адрес (улица или улица + номер дома):", reply_markup=reply_markup)
    return OBJECT_WAITING_ADDRESS


async def set_contacts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка контактов"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await delete_preview_and_menu(context, user.id)
    
    object_id = user_data[user.id]["object_id"]
    obj = await get_object(object_id)
    user_info = await get_user(str(user.id))
    
    phone = obj.get('phone_number', '')
    contact_name = obj.get('contact_name', '')
    show_username = obj.get('show_username', False)
    
    if not phone and user_info:
        phone = user_info.get('phone_number', '')
    
    text = f"<b>Настройка контактов</b>\n\n"
    text += f"Текущий номер: {phone if phone else 'Не указан'}\n"
    text += f"Имя: {contact_name if contact_name else 'Не указано'}\n"
    text += f"Указывать ник TG: {'Да' if show_username else 'Нет'}\n\n"
    text += "Выберите действие:"
    
    keyboard = [
        [InlineKeyboardButton("Использовать номер из настроек", callback_data="phone_from_settings_menu")],
        [InlineKeyboardButton("Указать другой номер", callback_data="phone_custom_menu")],
        [InlineKeyboardButton("Указать имя", callback_data="set_contact_name_menu")],
        [InlineKeyboardButton(f"Указывать ник TG: {'✅' if show_username else '❌'}", callback_data="toggle_show_username")],
        [InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_preview")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return OBJECT_WAITING_CONTACTS


async def edit_rooms_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактировать комнаты из меню"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await delete_preview_and_menu(context, user.id)
    
    rooms = await get_rooms_config()
    keyboard = []
    row = []
    for i, room in enumerate(rooms):
        row.append(InlineKeyboardButton(room, callback_data=f"rooms_{room}"))
        if len(row) == 3 or i == len(rooms) - 1:
            keyboard.append(row)
            row = []
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_preview")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(ADD_OBJECT_ROOMS_QUESTION, reply_markup=reply_markup)
    return OBJECT_WAITING_EDIT_ROOMS


async def edit_district_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактировать район из меню"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await delete_preview_and_menu(context, user.id)
    
    object_id = user_data[user.id]["object_id"]
    obj = await get_object(object_id)
    current_districts = obj.get('districts', [])
    
    # Очищаем текущие районы
    user_data[user.id]["districts"] = []
    await update_object(object_id, {"districts": []})
    
    districts_config = await get_districts_config()
    districts = list(districts_config.keys())
    
    keyboard = [[InlineKeyboardButton(district, callback_data=f"district_{district}")] 
                for district in districts]
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_preview")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text("Выберите район (текущие районы очищены):", reply_markup=reply_markup)
    return OBJECT_WAITING_EDIT_DISTRICT


async def edit_price_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактировать цену из меню"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await delete_preview_and_menu(context, user.id)
    
    await query.message.reply_text(ADD_OBJECT_PRICE_QUESTION)
    return OBJECT_WAITING_EDIT_PRICE


async def save_draft_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Автосохранение - просто уведомление"""
    query = update.callback_query
    await query.answer("✅ Автосохранение включено", show_alert=False)
    
    user = update.effective_user
    
    # Проверяем наличие user_data и сохраняем как черновик, если есть объект
    if user.id in user_data and "object_id" in user_data[user.id]:
        object_id = user_data[user.id]["object_id"]
        await update_object(object_id, {"status": "черновик"})
        await log_action("OBJECT_AUTO_SAVED", user.id, user.username, f"Object: {object_id}")
    
    # Не очищаем данные и не завершаем диалог - просто уведомление
    return OBJECT_PREVIEW_MENU


async def delete_current_object(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос подтверждения удаления текущего объекта"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    object_id = user_data.get(user.id, {}).get("object_id")

    if not object_id:
        await query.answer("Ошибка: данные объекта не найдены.", show_alert=True)
        return

    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data="delete_current_confirm"),
            InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_preview")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Вы уверены, что хотите удалить объявление?", reply_markup=reply_markup)


async def delete_current_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления текущего объекта"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    object_id = user_data.get(user.id, {}).get("object_id")

    if not object_id:
        await query.answer("Ошибка: данные объекта не найдены.", show_alert=True)
        return

    await delete_object(object_id)
    user_data.pop(user.id, None)

    keyboard = [[InlineKeyboardButton("🏠 На главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Объявление удалено.", reply_markup=reply_markup)


async def auto_publish_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню настроек автопубликации"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user = update.effective_user
    user_role = await get_user_role(str(user.id))
    
    # Проверяем доступ (автопубликация доступна для freepremium, premium и protime)
    if user_role not in [ROLE_FREEPREMIUM, ROLE_PREMIUM, ROLE_PROTIME]:
        keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = (
            "🔒 <b>Премиум доступ</b>\n\n"
            "Автопубликация доступна только для freepremium, premium и Pro Time пользователей."
        )
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return
    
    # Получаем настройки автопубликации
    settings = await get_user_autopublish_settings(str(user.id))
    global_enabled = settings.get("enabled", False)
    
    # Формируем текст статуса
    if not global_enabled:
        status_text = "Отключена"
    else:
        status_text = "Включена"
    
    # Формируем текст выбранного времени
    time_text = "Не выбрано"
    if settings.get("time_type") == "vip":
        time_text = "VIP очередь (8-9)"
    elif settings.get("time_type") == "default":
        time_text = "По умолчанию (9-12)"
    elif settings.get("time_type") == "slot" and settings.get("slot_time"):
        time_text = f"Слот {settings.get('slot_time')}"
    
    # Получаем объекты пользователя
    objects = await load_json("objects.json")
    user_objects = []
    for obj_id, obj in objects.items():
        if obj.get("user_id") == str(user.id):
            autopublish_enabled = obj.get("auto_publish_enabled", False)
            price = obj.get("price", 0)
            user_objects.append({
                "object_id": obj_id,
                "price": price,
                "autopublish_enabled": autopublish_enabled
            })
    
    # Формируем текст меню
    text = f"⚙️ <b>Настройки автопубликации</b>\n\n"
    text += f"<b>Статус автопубликации:</b> {status_text}\n"
    text += f"<b>Выбранное время:</b> {time_text}\n\n"
    # Помечаем последнее меню для сортировок
    context.user_data["last_sort_menu"] = "auto_publish"
    text += "Сортировка объектов для показа:\n"
    text += "• /sort_new — сначала новые\n"
    text += "• /sort_old — сначала старые\n"
    text += "После ввода команды вернемся в это меню.\n\n"
    
    # Кнопки меню
    global_toggle_text = "Общая автопубликация✅" if global_enabled else "Общая автопубликация❌"
    keyboard = [
        [InlineKeyboardButton(global_toggle_text, callback_data="toggle_user_autopublish")],
        [InlineKeyboardButton("Выбрать время", callback_data="publish_schedule_menu")],
    ]
    
    if user_objects:
        text += "<b>Объекты:</b>\n"
        for obj_data in user_objects:
            status_icon = "✅" if obj_data["autopublish_enabled"] else "❌"
            price = obj_data['price']
            # Убираем префикс obj_ из object_id, если он есть
            obj_id_clean = obj_data['object_id'].replace("obj_", "") if obj_data['object_id'].startswith("obj_") else obj_data['object_id']
            text += f"{price} тыс. руб. {status_icon}\n"
            text += f"Изменить /edit_obj_{obj_id_clean}\n\n"
    else:
        text += "У вас пока нет объектов.\n"
    
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def back_to_preview_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться к предпросмотру"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
    elif update.message:
        # Если это команда /skip
        pass
    else:
        return ConversationHandler.END
    
    user = update.effective_user
    
    # Проверяем наличие user_data
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        if update.callback_query:
            await update.callback_query.edit_message_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    obj = await get_object(object_id)
    user_info = await get_user(str(user.id))
    
    await show_object_preview_with_menu(update, context, obj, user_info)
    return OBJECT_PREVIEW_MENU


# Обработчики ввода данных для расширенных настроек

async def area_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода площади"""
    user = update.effective_user
    
    # Проверяем наличие user_data
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены. Начните заново.")
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    area = update.message.text.strip()
    
    if not area:
        await update.message.reply_text("Площадь не может быть пустой. Введите площадь в м²:")
        return OBJECT_WAITING_AREA
    
    await update_object(object_id, {"area": area})
    await log_action("OBJECT_AREA_SET", user.id, user.username, f"Area: {area}")
    
    # Проверяем, есть ли уже комментарий - если есть, значит это редактирование из меню
    obj = await get_object(object_id)
    if obj.get('comment'):
        # Это редактирование из меню - возвращаемся в меню
        user_info = await get_user(str(user.id))
        await show_object_preview_with_menu(update, context, obj, user_info)
        return OBJECT_PREVIEW_MENU
    
    # Это первый опрос - продолжаем
    rooms_type = obj.get('rooms_type', '')
    if rooms_type and rooms_type.lower() == 'дом':
        # Для дома пропускаем этаж и переходим к комментарию
        await update_object(object_id, {"floor": ""})
        await update.message.reply_text("Опишите квартиру и условия покупки: обременения и тп")
        return OBJECT_WAITING_COMMENT
    
    # Переход к обязательному вопросу об этаже
    await update.message.reply_text("Введите этаж:")
    return OBJECT_WAITING_FLOOR


async def floor_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода этажа"""
    user = update.effective_user
    
    # Проверяем наличие user_data
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены. Начните заново.")
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    floor = update.message.text.strip()
    
    if not floor:
        await update.message.reply_text("Этаж не может быть пустым. Введите этаж:")
        return OBJECT_WAITING_FLOOR
    
    await update_object(object_id, {"floor": floor})
    await log_action("OBJECT_FLOOR_SET", user.id, user.username, f"Floor: {floor}")
    
    # Проверяем, есть ли уже комментарий - если есть, значит это редактирование из меню
    obj = await get_object(object_id)
    if obj.get('comment'):
        # Это редактирование из меню - возвращаемся в меню
        user_info = await get_user(str(user.id))
        await show_object_preview_with_menu(update, context, obj, user_info)
        return OBJECT_PREVIEW_MENU
    
    # Это первый опрос - продолжаем к комментарию
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Опишите квартиру и условия покупки: обременения и тп", reply_markup=reply_markup)
    return OBJECT_WAITING_COMMENT


async def comment_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода комментария"""
    user = update.effective_user
    
    # Проверяем наличие user_data
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены. Начните заново.")
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    comment = update.message.text.strip()
    
    if not comment:
        await update.message.reply_text("Комментарий не может быть пустым. Опишите квартиру и условия покупки: обременения и тп")
        return OBJECT_WAITING_COMMENT
    
    await update_object(object_id, {"comment": comment})
    await log_action("OBJECT_COMMENT_SET", user.id, user.username, f"Comment: {comment[:50]}...")
    
    # Переход к предпросмотру с меню доп настроек
    obj = await get_object(object_id)
    user_info = await get_user(str(user.id))
    await show_object_preview_with_menu(update, context, obj, user_info)
    return OBJECT_PREVIEW_MENU


async def renovation_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора состояния ремонта"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Проверяем наличие user_data
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await query.edit_message_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    renovation = query.data.replace("renovation_", "")
    
    await update_object(object_id, {"renovation": renovation})
    await log_action("OBJECT_RENOVATION_SET", user.id, user.username, f"Renovation: {renovation}")
    
    obj = await get_object(object_id)
    user_info = await get_user(str(user.id))
    await show_object_preview_with_menu(update, context, obj, user_info)
    return OBJECT_PREVIEW_MENU


async def address_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода адреса"""
    user = update.effective_user
    
    # Проверяем наличие user_data
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены. Начните заново.")
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    address = update.message.text.strip()
    
    await update_object(object_id, {"address": address})
    await log_action("OBJECT_ADDRESS_SET", user.id, user.username, f"Address: {address}")
    
    obj = await get_object(object_id)
    user_info = await get_user(str(user.id))
    await show_object_preview_with_menu(update, context, obj, user_info)
    return OBJECT_PREVIEW_MENU


async def contact_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода имени контакта"""
    user = update.effective_user
    
    # Проверяем наличие user_data
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены. Начните заново.")
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    name = update.message.text.strip()
    
    await update_object(object_id, {"contact_name": name})
    await log_action("OBJECT_CONTACT_NAME_SET", user.id, user.username, f"Name: {name}")
    
    obj = await get_object(object_id)
    user_info = await get_user(str(user.id))
    await show_object_preview_with_menu(update, context, obj, user_info)
    return OBJECT_PREVIEW_MENU


async def phone_from_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Использовать номер из настроек из меню"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    object_id = user_data[user.id]["object_id"]
    user_info = await get_user(str(user.id))
    phone = user_info.get("phone_number", "") if user_info else ""
    
    if phone:
        await update_object(object_id, {"phone_number": phone})
        await log_action("OBJECT_PHONE_SET_FROM_SETTINGS", user.id, user.username, f"Phone: {phone}")
    
    obj = await get_object(object_id)
    await show_object_preview_with_menu(update, context, obj, user_info)
    return OBJECT_PREVIEW_MENU


async def phone_custom_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Указать другой номер из меню"""
    query = update.callback_query
    await query.answer()
    
    text = "Введите номер телефона:\n\n"
    text += "Номер в формате:\n"
    text += "89693386969"
    
    keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, text, reply_markup=reply_markup)
    return OBJECT_WAITING_CONTACTS


async def phone_custom_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода номера телефона из меню"""
    user = update.effective_user
    
    # Проверяем наличие user_data
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены. Начните заново.")
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    phone = update.message.text.strip()
    
    if not phone or len(phone) < 10:
        text = "Некорректный номер телефона. Попробуйте еще раз.\n\n"
        text += "Номер в формате:\n"
        text += "89693386969"
        keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_preview")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup)
        return OBJECT_WAITING_CONTACTS
    
    await update_object(object_id, {"phone_number": phone})
    await log_action("OBJECT_PHONE_SET_CUSTOM", user.id, user.username, f"Phone: {phone}")
    
    obj = await get_object(object_id)
    user_info = await get_user(str(user.id))
    await show_object_preview_with_menu(update, context, obj, user_info)
    return OBJECT_PREVIEW_MENU


async def toggle_show_username_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключить показ username"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    object_id = user_data[user.id]["object_id"]
    obj = await get_object(object_id)
    
    current_value = obj.get('show_username', False)
    await update_object(object_id, {"show_username": not current_value})
    
    obj = await get_object(object_id)
    user_info = await get_user(str(user.id))
    await show_object_preview_with_menu(update, context, obj, user_info)
    return OBJECT_PREVIEW_MENU


async def edit_rooms_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка редактирования комнат"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Проверяем наличие user_data
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await query.edit_message_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    rooms_type = query.data.replace("rooms_", "")
    object_id = user_data[user.id]["object_id"]
    
    await update_object(object_id, {"rooms_type": rooms_type})
    await log_action("OBJECT_ROOMS_EDITED", user.id, user.username, f"Rooms: {rooms_type}")
    
    obj = await get_object(object_id)
    user_info = await get_user(str(user.id))
    await show_object_preview_with_menu(update, context, obj, user_info)
    return OBJECT_PREVIEW_MENU


async def edit_district_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка редактирования района"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Проверяем наличие user_data
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await query.edit_message_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    district = query.data.replace("district_", "")
    object_id = user_data[user.id]["object_id"]
    
    if "districts" not in user_data[user.id]:
        user_data[user.id]["districts"] = []
    
    if district not in user_data[user.id]["districts"]:
        user_data[user.id]["districts"].append(district)
    
    await update_object(object_id, {"districts": user_data[user.id]["districts"]})
    await log_action("OBJECT_DISTRICT_EDITED", user.id, user.username, f"District: {district}")
    
    obj = await get_object(object_id)
    user_info = await get_user(str(user.id))
    await show_object_preview_with_menu(update, context, obj, user_info)
    return OBJECT_PREVIEW_MENU


async def edit_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка редактирования цены"""
    user = update.effective_user
    
    # Проверяем наличие user_data
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены. Начните заново.")
        return ConversationHandler.END
    
    try:
        price = float(update.message.text.replace(",", "."))
        if price <= 0:
            raise ValueError
        
        object_id = user_data[user.id]["object_id"]
        await update_object(object_id, {"price": price})
        await log_action("OBJECT_PRICE_EDITED", user.id, user.username, f"Price: {price}")
        
        obj = await get_object(object_id)
        user_info = await get_user(str(user.id))
        await show_object_preview_with_menu(update, context, obj, user_info)
        return OBJECT_PREVIEW_MENU
        
    except ValueError:
        await update.message.reply_text(ERROR_INVALID_PRICE)
        return OBJECT_WAITING_EDIT_PRICE


async def add_district_from_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавить район из меню расширенных настроек"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    district = query.data.replace("district_", "")
    object_id = user_data[user.id]["object_id"]
    
    obj = await get_object(object_id)
    current_districts = obj.get('districts', [])
    
    if district not in current_districts:
        current_districts.append(district)
        await update_object(object_id, {"districts": current_districts})
        user_data[user.id]["districts"] = current_districts
        await log_action("OBJECT_DISTRICT_ADDED", user.id, user.username, f"District: {district}")
    
    obj = await get_object(object_id)
    user_info = await get_user(str(user.id))
    await show_object_preview_with_menu(update, context, obj, user_info)
    return OBJECT_PREVIEW_MENU


async def media_added_from_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка добавления медиа из меню"""
    user = update.effective_user
    
    # Проверяем наличие user_data
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены. Начните заново.")
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    
    obj = await get_object(object_id)
    media_files = obj.get("media_files", [])
    
    if len(media_files) >= 10:
        await update.message.reply_text("Достигнут лимит в 10 медиафайлов.")
        obj = await get_object(object_id)
        user_info = await get_user(str(user.id))
        await show_object_preview_with_menu(update, context, obj, user_info)
        return OBJECT_PREVIEW_MENU
    
    file_id = None
    media_type = None
    
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.video:
        file_id = update.message.video.file_id
        media_type = "video"
    else:
        await update.message.reply_text("Пожалуйста, отправьте фото или видео.")
        return OBJECT_WAITING_MEDIA
    
    # Проверяем, является ли это частью media_group
    is_media_group = update.message.media_group_id is not None
    
    if is_media_group:
        group_id_key = f"media_group_{update.message.media_group_id}"
        
        # Инициализируем данные группы, если это первое сообщение
        if group_id_key not in user_data[user.id]:
            user_data[user.id][group_id_key] = {
                "preview_sent": False,
                "count": 0,
                "task_started": False
            }
        
        # Увеличиваем счетчик ДО сохранения
        user_data[user.id][group_id_key]["count"] += 1
        current_count = user_data[user.id][group_id_key]["count"]
        
        # Сохраняем файл в объект
        media_files.append({"file_id": file_id, "type": media_type})
        await update_object(object_id, {"media_files": media_files})
        
        await log_action("OBJECT_MEDIA_ADDED", user.id, user.username, f"Media type: {media_type}, Total: {len(media_files)}, Group: {is_media_group}, Count in group: {current_count}")
        
        # Если это первое сообщение группы, запускаем асинхронную задачу для показа предпросмотра
        if current_count == 1 and not user_data[user.id][group_id_key]["task_started"]:
            user_data[user.id][group_id_key]["task_started"] = True
            
            # Сохраняем необходимые данные для асинхронной задачи
            saved_user_id = user.id
            saved_message = update.message
            saved_context = context
            
            # Запускаем асинхронную задачу для ожидания всех файлов
            async def wait_and_show_preview():
                # Сначала ждем минимум 1 секунду, чтобы дать время прийти всем файлам
                await asyncio.sleep(1.0)
                
                # Ждем и проверяем, что все файлы загружены
                max_wait_time = 10  # Максимальное время ожидания в секундах
                check_interval = 0.5  # Интервал проверки в секундах
                waited_time = 1.0  # Уже подождали 1 секунду
                stable_count = 0
                previous_count = 0
                
                while waited_time < max_wait_time:
                    # Получаем актуальный объект со всеми файлами из группы
                    obj = await get_object(object_id)
                    current_files_count = len(obj.get("media_files", []))
                    
                    # Если количество файлов не изменилось, увеличиваем счетчик стабильности
                    if current_files_count == previous_count and previous_count > 0:
                        stable_count += check_interval
                    else:
                        stable_count = 0
                        previous_count = current_files_count
                    
                    # Если количество файлов не менялось 2 секунды, считаем что все загружено
                    if stable_count >= 2.0 and previous_count > 0:
                        break
                    
                    await asyncio.sleep(check_interval)
                    waited_time += check_interval
                
                # Проверяем, не был ли уже отправлен предпросмотр
                if saved_user_id in user_data and group_id_key in user_data[saved_user_id]:
                    if not user_data[saved_user_id][group_id_key]["preview_sent"]:
                        # Получаем финальный объект со всеми файлами
                        obj = await get_object(object_id)
                        # Устанавливаем флаг ДО вызова функции, чтобы предотвратить повторные вызовы
                        user_data[saved_user_id][group_id_key]["preview_sent"] = True
                        user_info = await get_user(str(saved_user_id))
                        
                        # Создаем минимальный update для функции
                        class FakeUpdate:
                            def __init__(self, message):
                                self.message = message
                                self.callback_query = None
                                self.effective_user = message.from_user
                        
                        fake_update = FakeUpdate(saved_message)
                        
                        # Отправляем предпросмотр только один раз для всей группы
                        await show_object_preview_with_menu(fake_update, saved_context, obj, user_info)
                        
                        # Очищаем временные данные группы
                        if group_id_key in user_data[saved_user_id]:
                            del user_data[saved_user_id][group_id_key]
            
            # Запускаем задачу в фоне
            asyncio.create_task(wait_and_show_preview())
        
        return OBJECT_WAITING_MEDIA
    else:
        # Обычное одиночное медиа - сохраняем и показываем предпросмотр сразу
        media_files.append({"file_id": file_id, "type": media_type})
        await update_object(object_id, {"media_files": media_files})
        
        await log_action("OBJECT_MEDIA_ADDED", user.id, user.username, f"Media type: {media_type}, Total: {len(media_files)}")
        
        obj = await get_object(object_id)
        user_info = await get_user(str(user.id))
        await show_object_preview_with_menu(update, context, obj, user_info)
    
    return OBJECT_PREVIEW_MENU


async def set_contact_name_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс указания имени из меню контактов"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await safe_edit_message(query, "Введите имя контакта:", reply_markup=reply_markup)
    return OBJECT_WAITING_NAME


async def contact_name_input_from_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода имени контакта из меню"""
    user = update.effective_user
    
    # Проверяем наличие user_data
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены. Начните заново.")
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    name = update.message.text.strip()
    
    await update_object(object_id, {"contact_name": name})
    await log_action("OBJECT_CONTACT_NAME_SET", user.id, user.username, f"Name: {name}")
    
    obj = await get_object(object_id)
    user_info = await get_user(str(user.id))
    await show_object_preview_with_menu(update, context, obj, user_info)
    return OBJECT_PREVIEW_MENU


async def show_publication_time_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню выбора времени публикации"""
    logger.info(f"SHOW_PUBLICATION_TIME_MENU_START - Update type: {type(update)}, Has callback_query: {update.callback_query is not None}")
    # Логируем СРАЗУ в начале функции
    await log_action("SHOW_PUBLICATION_TIME_MENU_START", update.effective_user.id if update.effective_user else None, 
                    update.effective_user.username if update.effective_user else None, 
                    f"Update type: {type(update)}, Has callback_query: {update.callback_query is not None}")
    
    query = update.callback_query
    if not query:
        logger.error("SHOW_PUBLICATION_TIME_MENU_ERROR_NO_QUERY - No callback_query in update")
        await log_action("SHOW_PUBLICATION_TIME_MENU_ERROR_NO_QUERY", update.effective_user.id if update.effective_user else None, 
                        update.effective_user.username if update.effective_user else None, "No callback_query in update")
        return ConversationHandler.END
    
    await query.answer()
    logger.info(f"SHOW_PUBLICATION_TIME_MENU_ANSWERED - Callback data: {query.data}")
    await log_action("SHOW_PUBLICATION_TIME_MENU_ANSWERED", query.from_user.id if query.from_user else None, 
                    query.from_user.username if query.from_user else None, f"Callback data: {query.data}")
    
    user = update.effective_user
    logger.info(f"SHOW_PUBLICATION_TIME_MENU_CALLED - User: {user.id}, Callback data: {query.data}")
    await log_action("SHOW_PUBLICATION_TIME_MENU_CALLED", user.id, user.username, f"Callback data: {query.data}")
    
    user_role = await get_user_role(str(user.id))
    logger.info(f"SHOW_PUBLICATION_TIME_MENU_USER_ROLE - User: {user.id}, Role: {user_role}")
    await log_action("SHOW_PUBLICATION_TIME_MENU_USER_ROLE", user.id, user.username, f"Role: {user_role}")
    
    # Получаем object_id
    object_id = None
    logger.info(f"Getting object_id - user_data keys: {list(user_data.get(user.id, {}).keys())}, callback_data: {query.data}")
    if user.id in user_data and "object_id" in user_data[user.id]:
        object_id = user_data[user.id]["object_id"]
        logger.info(f"Got object_id from user_data: {object_id}")
        await log_action("SHOW_PUBLICATION_TIME_MENU_OBJECT_FROM_USER_DATA", user.id, user.username, f"Object: {object_id}")
    elif query.data.startswith("publish_draft_"):
        object_id = query.data.replace("publish_draft_", "")
        logger.info(f"Got object_id from callback_data: {object_id}")
        await log_action("SHOW_PUBLICATION_TIME_MENU_OBJECT_FROM_CALLBACK", user.id, user.username, f"Object: {object_id}")
    
    if not object_id:
        logger.error(f"SHOW_PUBLICATION_TIME_MENU_ERROR_NO_OBJECT - User: {user.id}, user_data keys: {list(user_data.get(user.id, {}).keys())}")
        await log_action("SHOW_PUBLICATION_TIME_MENU_ERROR_NO_OBJECT", user.id, user.username, f"user_data keys: {list(user_data.get(user.id, {}).keys())}")
        await query.edit_message_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    # Free пользователи могут только публиковать сразу
    if user_role == ROLE_FREE:
        logger.info(f"SHOW_PUBLICATION_TIME_MENU_FREE_USER - Publishing immediately, Object: {object_id}")
        await log_action("SHOW_PUBLICATION_TIME_MENU_FREE_USER", user.id, user.username, f"Publishing immediately, Object: {object_id}")
        await publish_object_immediate(update, context, object_id)
        return ConversationHandler.END
    
    # Для freepremium и premium показываем меню выбора времени
    if user_role in [ROLE_FREEPREMIUM, ROLE_PREMIUM]:
        logger.info(f"SHOW_PUBLICATION_TIME_MENU_SHOWING_MENU - Object: {object_id}, Role: {user_role}")
        await log_action("SHOW_PUBLICATION_TIME_MENU_SHOWING_MENU", user.id, user.username, f"Object: {object_id}, Role: {user_role}")
        keyboard = [
            [InlineKeyboardButton("🚀 Опубликовать сразу", callback_data=f"publish_immediate_{object_id}")],
            [InlineKeyboardButton("⏰ Выбрать время публикации", callback_data=f"publish_schedule_{object_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            logger.info(f"Editing message for publication menu - Object: {object_id}")
            await query.edit_message_text(
                "Выберите способ публикации:\n\n"
                "• Опубликовать сразу - объект будет опубликован немедленно\n"
                "• Выбрать время - вы сможете выбрать временной слот",
                reply_markup=reply_markup
            )
            logger.info(f"SHOW_PUBLICATION_TIME_MENU_SUCCESS - Object: {object_id}")
            await log_action("SHOW_PUBLICATION_TIME_MENU_SUCCESS", user.id, user.username, f"Object: {object_id}")
        except Exception as e:
            logger.error(f"SHOW_PUBLICATION_TIME_MENU_ERROR - Error: {str(e)}, Object: {object_id}", exc_info=True)
            await log_action("SHOW_PUBLICATION_TIME_MENU_ERROR", user.id, user.username, f"Error: {str(e)}, Object: {object_id}")
            raise
        return OBJECT_PREVIEW_MENU
    else:
        # Для остальных ролей - только сразу
        await log_action("SHOW_PUBLICATION_TIME_MENU_OTHER_ROLE", user.id, user.username, f"Publishing immediately, Object: {object_id}, Role: {user_role}")
        await publish_object_immediate(update, context, object_id)
        return ConversationHandler.END


async def get_target_chats_for_object(obj: Dict) -> List[str]:
    """Определить целевые чаты для объекта"""
    target_chats = []
    
    # 1. По типу комнат
    rooms_type = obj.get('rooms_type', '')
    chats = await get_chats()
    for chat_id, chat_data in chats.items():
        if chat_data.get('type') == 'rooms' and chat_data.get('params') == rooms_type:
            target_chats.append(chat_id)
    
    # 2. По районам
    districts = obj.get('districts', [])
    districts_config = await get_districts_config()
    
    # Добавление родительских районов
    all_districts = set(districts)
    for district in districts:
        if district in districts_config:
            parent_districts = districts_config[district]
            all_districts.update(parent_districts)
    
    for district in all_districts:
        for chat_id, chat_data in chats.items():
            if chat_data.get('type') == 'district' and chat_data.get('params') == district:
                if chat_id not in target_chats:
                    target_chats.append(chat_id)
    
    # 3. По цене
    price = obj.get('price', 0)
    price_ranges = await get_price_ranges()
    for range_name, range_values in price_ranges.items():
        if range_values[0] <= price < range_values[1]:
            for chat_id, chat_data in chats.items():
                if chat_data.get('type') == 'price_range':
                    chat_params = chat_data.get('params', [])
                    if isinstance(chat_params, list) and len(chat_params) == 2:
                        if chat_params[0] == range_values[0] and chat_params[1] == range_values[1]:
                            if chat_id not in target_chats:
                                target_chats.append(chat_id)
    
    return target_chats


async def publish_immediate_current(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка 'Опубликовать сейчас' из меню настроек - показывает предпросмотр и список чатов"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    object_id = user_data.get(user.id, {}).get("object_id")

    if not object_id:
        await query.answer("Ошибка: данные объекта не найдены.", show_alert=True)
        return OBJECT_PREVIEW_MENU

    obj = await get_object(object_id)
    if not obj:
        await query.answer("Ошибка: объект не найден.", show_alert=True)
        return OBJECT_PREVIEW_MENU

    # Проверяем наличие контактов (телефон или username)
    user_info = await get_user(str(user.id))
    phone = obj.get('phone_number', '')
    if not phone and user_info:
        phone = user_info.get('phone_number', '')
    
    show_username = obj.get('show_username', False)
    has_username = show_username and user_info and user_info.get('username')
    
    if not phone and not has_username:
        # Нет ни телефона, ни username - предупреждаем и предлагаем ввести номер
        warning_text = "⚠️ <b>Внимание!</b>\n\n"
        warning_text += "С вами не смогут связаться, так как не указан номер телефона и не включен ник Telegram.\n\n"
        warning_text += "Пожалуйста, укажите номер телефона для публикации."
        
        keyboard = [
            [InlineKeyboardButton("Указать номер телефона", callback_data="set_contacts")],
            [InlineKeyboardButton("Назад к редактированию", callback_data="back_to_preview")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.message.reply_text(warning_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        except Exception as e:
            try:
                await query.edit_message_text(warning_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            except Exception as e2:
                logger.error(f"Error sending warning message: {e2}")
        
        return OBJECT_PREVIEW_MENU

    try:
        # Получаем целевые чаты
        target_chats = await get_target_chats_for_object(obj)
        
        # Получаем названия чатов
        chats = await get_chats()
        chat_names = []
        for chat_id in target_chats:
            chat_data = chats.get(chat_id, {})
            chat_title = chat_data.get('title', f'Чат {chat_id}')
            chat_names.append(chat_title)
        
        # Формируем текст со списком чатов
        if chat_names:
            chats_text = "Объявление будет опубликовано в следующие чаты:\n\n"
            for i, name in enumerate(chat_names, 1):
                chats_text += f"{i}. {name}\n"
        else:
            chats_text = "⚠️ Не найдены подходящие чаты для публикации.\n\n"
            chats_text += "Возможные причины:\n"
            chats_text += "• Чаты еще не настроены администратором\n"
            chats_text += "• Нет чатов, соответствующих параметрам объекта"
        
        # Кнопки подтверждения
        keyboard = []
        if chat_names:
            keyboard.append([InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_publish_{object_id}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад к редактированию", callback_data="back_to_preview")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем сообщение со списком чатов (используем query.message напрямую)
        try:
            await query.message.reply_text(chats_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error sending chats list message: {e}", exc_info=True)
            # Если не получилось отправить через reply, пробуем через edit
            try:
                await query.edit_message_text(chats_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            except Exception as e2:
                logger.error(f"Error editing message: {e2}", exc_info=True)
        
        return OBJECT_PREVIEW_MENU
    except Exception as e:
        logger.error(f"Error in publish_immediate_current: {e}", exc_info=True)
        await query.answer(f"Ошибка: {str(e)}", show_alert=True)
        return OBJECT_PREVIEW_MENU


async def confirm_publish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик подтверждения публикации"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("confirm_publish_", "")
    user = update.effective_user
    
    # Сохраняем object_id во временные данные для функции публикации
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    # Вызываем функцию публикации
    try:
        await publish_object_immediate(update, context, object_id)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in confirm_publish_handler: {e}", exc_info=True)
        await query.answer(f"Ошибка при публикации: {str(e)}", show_alert=True)
        return OBJECT_PREVIEW_MENU


async def publish_schedule_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Выбрать время' - показывает меню выбора времени для автопубликации"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_role = await get_user_role(str(user.id))
    
    # Показываем меню выбора времени для всех ролей, но с ограничениями
    keyboard = []
    
    # VIP очередь (8-9) – показываем всем, но доступна только для Pro Time
    if user_role == ROLE_PROTIME:
        keyboard.append([InlineKeyboardButton("С 8 до 9 (VIP очередь)", callback_data="autopublish_time_vip")])
    else:
        keyboard.append([InlineKeyboardButton("С 8 до 9 (VIP очередь) 🔒", callback_data="autopublish_time_vip")])
    
    # Очередь по умолчанию (9-12) – показываем всем, но доступна только для freepremium, premium и Pro Time
    if user_role in [ROLE_FREEPREMIUM, ROLE_PREMIUM, ROLE_PROTIME]:
        keyboard.append([InlineKeyboardButton("С 9 до 12 (по умолчанию)", callback_data="autopublish_time_default")])
    else:
        keyboard.append([InlineKeyboardButton("С 9 до 12 (по умолчанию) 🔒", callback_data="autopublish_time_default")])
    
    # Слоты 12-22 – показываем всем, но доступны только для premium и Pro Time
    if user_role in [ROLE_PREMIUM, ROLE_PROTIME]:
        keyboard.append([InlineKeyboardButton("С 12 до 22 (выбрать слот)", callback_data="autopublish_time_slots")])
    else:
        keyboard.append([InlineKeyboardButton("С 12 до 22 (выбрать слот) 🔒", callback_data="autopublish_time_slots")])
    
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="auto_publish_settings")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "⏰ <b>МЕНЮ ВЫБОРА ВРЕМЕНИ</b>\n\n"
        "Выберите время для автопубликации:\n\n"
        "• <b>С 8 до 9</b> - VIP очередь (только для Pro Time)\n"
        "• <b>С 9 до 12</b> - очередь по умолчанию (для freepremium, premium и Pro Time)\n"
        "• <b>С 12 до 22</b> - выбрать конкретный слот (для premium и Pro Time)\n\n"
        "🔒 - недоступно для вашей роли",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def autopublish_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора времени автопубликации"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_role = await get_user_role(str(user.id))
    time_type = query.data.replace("autopublish_time_", "")
    
    if time_type == "vip":
        # VIP очередь доступна только для роли Pro Time
        if user_role != ROLE_PROTIME:
            await query.answer("Это недоступно для вас", show_alert=True)
            return
        # Устанавливаем VIP очередь (8-9)
        await set_user_autopublish_settings(str(user.id), enabled=True, time_type="vip", slot_time=None)
        await query.answer("✅ Время автопубликации установлено: VIP очередь (8-9)", show_alert=True)
        # Возвращаемся в меню настроек
        await auto_publish_settings(update, context)
    elif time_type == "default":
        # Очередь по умолчанию доступна для freepremium, premium и Pro Time
        if user_role not in [ROLE_FREEPREMIUM, ROLE_PREMIUM, ROLE_PROTIME]:
            await query.answer("Это недоступно для вас", show_alert=True)
            return
        # Устанавливаем очередь по умолчанию (9-12)
        await set_user_autopublish_settings(str(user.id), enabled=True, time_type="default", slot_time=None)
        await query.answer("✅ Время автопубликации установлено: по умолчанию (9-12)", show_alert=True)
        # Возвращаемся в меню настроек
        await auto_publish_settings(update, context)
    elif time_type == "slots":
        # Слоты 12-22 доступны для premium и Pro Time
        if user_role not in [ROLE_PREMIUM, ROLE_PROTIME]:
            await query.answer("Это недоступно для вас", show_alert=True)
            return
        # Показываем меню выбора слотов
        await show_autopublish_slots_menu(update, context)
        return


async def show_autopublish_slots_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню выбора слотов для автопубликации"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_role = await get_user_role(str(user.id))
    
    # Дополнительная проверка доступа к слотам (premium и Pro Time)
    if user_role not in [ROLE_PREMIUM, ROLE_PROTIME]:
        await query.answer("Это недоступно для вас", show_alert=True)
        return
    
    # Получаем доступные слоты на сегодня
    today = format_moscow_datetime(format_str="%Y-%m-%d")
    today_slots = await get_available_slots(today, str(user.id))
    
    # Фильтруем только слоты 12-22
    custom_slots = [s for s in today_slots if s["type"] == SLOT_CUSTOM_12_22 and s["available"]]
    
    keyboard = []
    row = []
    for i, slot in enumerate(custom_slots):
        # Показываем, занят ли слот этим пользователем
        slot_text = slot["time"]
        if slot.get("booked_by") == str(user.id):
            slot_text += " ✅"
        row.append(InlineKeyboardButton(slot_text, callback_data=f"autopublish_slot_{slot['slot_id']}"))
        if len(row) == 3 or i == len(custom_slots) - 1:
            keyboard.append(row)
            row = []
    
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="auto_publish_settings")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⏰ <b>Выберите слот для автопубликации</b>\n\n"
        "Все ваши объекты с включенной автопубликацией будут публиковаться в выбранное время.\n"
        "Слот будет заблокирован для других пользователей.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def autopublish_slot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора конкретного слота для автопубликации"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_role = await get_user_role(str(user.id))
    
    # Слоты доступны только для premium и Pro Time
    if user_role not in [ROLE_PREMIUM, ROLE_PROTIME]:
        await query.answer("Это недоступно для вас", show_alert=True)
        return
    slot_id = query.data.replace("autopublish_slot_", "")
    
    # Бронируем слот для пользователя
    today = format_moscow_datetime(format_str="%Y-%m-%d")
    success = await book_time_slot(today, slot_id, user.id, None)
    
    if not success:
        await query.answer("Этот слот уже занят другим пользователем.", show_alert=True)
        return
    
    # Получаем время слота
    slot_time = slot_id.replace("slot_", "")
    time_str = f"{slot_time[:2]}:{slot_time[2:]}"
    
    # Устанавливаем настройки автопубликации
    await set_user_autopublish_settings(str(user.id), enabled=True, time_type="slot", slot_time=time_str)
    
    await query.answer(f"✅ Слот {time_str} выбран для автопубликации", show_alert=True)
    
    # Возвращаемся в меню настроек автопубликации
    await auto_publish_settings(update, context)


async def edit_object_from_autopublish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик редактирования объекта из меню автопубликации"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    object_id = query.data.replace("edit_object_from_autopublish_", "")
    
    # Проверяем, что объект существует и принадлежит пользователю
    obj = await get_object(object_id)
    if not obj:
        await query.answer("Объект не найден.", show_alert=True)
        return
    
    if obj.get("user_id") != str(user.id):
        await query.answer("Этот объект вам не принадлежит.", show_alert=True)
        return
    
    # Инициализация временных данных для редактирования
    user_data[user.id] = {
        "object_id": object_id,
        "districts": obj.get("districts", [])
    }
    
    # Показываем предпросмотр с меню расширенных настроек
    user_info = await get_user(str(user.id))
    await show_object_preview_with_menu(update, context, obj, user_info)
    
    # Устанавливаем состояние ConversationHandler
    context.user_data["_conversation_state"] = OBJECT_PREVIEW_MENU
    context.user_data["_conversation_name"] = "add_object_handler"
    
    return OBJECT_PREVIEW_MENU


async def edit_object_from_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик редактирования объекта из списка 'Мои объекты'"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    object_id = query.data.replace("edit_object_from_list_", "")
    
    # Проверяем, что объект существует и принадлежит пользователю
    obj = await get_object(object_id)
    if not obj:
        await query.answer("Объект не найден.", show_alert=True)
        return
    
    if obj.get("user_id") != str(user.id):
        await query.answer("Этот объект вам не принадлежит.", show_alert=True)
        return
    
    # Инициализация временных данных для редактирования
    user_data[user.id] = {
        "object_id": object_id,
        "districts": obj.get("districts", [])
    }
    
    # Показываем предпросмотр с меню расширенных настроек
    user_info = await get_user(str(user.id))
    await show_object_preview_with_menu(update, context, obj, user_info)
    
    # Устанавливаем состояние ConversationHandler
    context.user_data["_conversation_state"] = OBJECT_PREVIEW_MENU
    context.user_data["_conversation_name"] = "add_object_handler"
    
    return OBJECT_PREVIEW_MENU


async def delete_object_from_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик удаления объекта из списка 'Мои объекты'"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    object_id = query.data.replace("delete_object_from_list_", "")
    
    # Проверяем, что объект существует и принадлежит пользователю
    obj = await get_object(object_id)
    if not obj:
        await query.answer("Объект не найден.", show_alert=True)
        return
    
    if obj.get("user_id") != str(user.id):
        await query.answer("Этот объект вам не принадлежит.", show_alert=True)
        return
    
    # Показываем подтверждение удаления
    rooms = obj.get('rooms_type', 'Не указано')
    price = obj.get('price', 0)
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{object_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data="my_objects")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚠️ <b>Подтвердите удаление объекта:</b>\n\n"
        f"• {rooms} | {price} тыс. руб.\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def toggle_autopublish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик переключения автопубликации для объекта"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Получаем object_id
    object_id = None
    if user.id in user_data and "object_id" in user_data[user.id]:
        object_id = user_data[user.id]["object_id"]
    
    if not object_id:
        await query.answer("Ошибка: данные объекта не найдены.", show_alert=True)
        return
    
    # Проверяем доступ (для freepremium, premium и Pro Time)
    user_role = await get_user_role(str(user.id))
    if user_role not in [ROLE_FREEPREMIUM, ROLE_PREMIUM, ROLE_PROTIME]:
        await query.answer("Автопубликация доступна только для freepremium, premium и Pro Time пользователей.", show_alert=True)
        return
    
    # Переключаем автопубликацию
    current_status = await get_object_autopublish_enabled(object_id)
    new_status = not current_status
    await set_object_autopublish_enabled(object_id, new_status)
    
    # Обновляем меню объекта
    obj = await get_object(object_id)
    user_info = await get_user(str(user.id))
    await show_object_preview_with_menu(update, context, obj, user_info)
    
    return OBJECT_PREVIEW_MENU


async def show_date_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать слоты на конкретную дату"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.replace("date_", "").split("_")
    if len(parts) < 4:
        await query.edit_message_text("Ошибка: неверный формат данных.")
        return
    date = f"{parts[0]}_{parts[1]}_{parts[2]}"
    object_id = parts[3]
    
    slots = await get_available_slots(date)
    custom_slots = [s for s in slots if s["type"] == SLOT_CUSTOM_12_22 and s["available"]]
    
    keyboard = []
    row = []
    for i, slot in enumerate(custom_slots):
        row.append(InlineKeyboardButton(slot["time"], callback_data=f"slot_{date}_{slot['slot_id']}_{object_id}"))
        if len(row) == 3 or i == len(custom_slots) - 1:
            keyboard.append(row)
            row = []
    
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data=f"publish_schedule_{object_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    date_str = date.replace("_", "-")
    await query.edit_message_text(f"Выберите время на {date_str}:", reply_markup=reply_markup)


async def select_time_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора временного слота"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.replace("slot_", "").split("_")
    if len(parts) < 5:
        await query.answer("Ошибка: неверный формат данных.", show_alert=True)
        return
    date = f"{parts[0]}_{parts[1]}_{parts[2]}"
    slot_id = parts[3]
    object_id = parts[4]
    
    user = update.effective_user
    
    # Бронируем слот
    success = await book_time_slot(date, slot_id, user.id, object_id)
    
    if not success:
        await query.answer("Этот слот уже занят. Выберите другой.", show_alert=True)
        return
    
    # Обновляем объект
    date_str = date.replace("_", "-")
    slot_time = slot_id.replace("slot_", "")
    scheduled_datetime = f"{date_str} {slot_time[:2]}:{slot_time[2:]}"
    
    await update_object(object_id, {
        "status": "запланировано",
        "scheduled_time": scheduled_datetime,
        "scheduled_slot": slot_id,
        "publication_type": "scheduled"
    })
    
    await log_action("OBJECT_SCHEDULED", user.id, user.username, 
                    f"Object: {object_id}, Time: {scheduled_datetime}")
    
    keyboard = [[InlineKeyboardButton("🏠 На главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"✅ Объект запланирован на публикацию:\n"
        f"📅 Дата: {date_str}\n"
        f"⏰ Время: {slot_time[:2]}:{slot_time[2:]}\n\n"
        f"Объект будет автоматически опубликован в указанное время.",
        reply_markup=reply_markup
    )
    
    # Очистка временных данных
    if user.id in user_data:
        del user_data[user.id]
    
    return ConversationHandler.END


async def publish_object_immediate(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: str = None):
    """Немедленная публикация объекта в чаты"""
    logger.info(f"publish_object_immediate called - Update type: {type(update)}, Has callback_query: {update.callback_query is not None}")
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if not object_id:
            if query.data.startswith("publish_immediate_"):
                object_id = query.data.replace("publish_immediate_", "")
                logger.info(f"Extracted object_id from callback_data: {object_id}")
    else:
        query = None
    
    user = update.effective_user
    logger.info(f"User: {user.id} (@{user.username if user.username else 'N/A'})")
    
    if not object_id:
        if user.id in user_data and "object_id" in user_data[user.id]:
            object_id = user_data[user.id]["object_id"]
            logger.info(f"Got object_id from user_data: {object_id}")
        else:
            logger.error(f"PUBLISH_ERROR_NO_USER_DATA - User: {user.id}, user_data keys: {list(user_data.get(user.id, {}).keys())}")
            await log_action("PUBLISH_ERROR_NO_USER_DATA", user.id, user.username)
            if query:
                await query.edit_message_text("Ошибка: данные объекта не найдены.")
            return ConversationHandler.END
    
    logger.info(f"PUBLISH_OBJECT_CLICKED - Object: {object_id}, Type: immediate")
    await log_action("PUBLISH_OBJECT_CLICKED", user.id, user.username, f"Object: {object_id}, Type: immediate")
    
    obj = await get_object(object_id)
    if not obj:
        logger.error(f"Object not found: {object_id}")
        if query:
            await query.edit_message_text("Ошибка: объект не найден.")
        return ConversationHandler.END
    
    logger.info(f"Object found: {object_id}, Media count: {len(obj.get('media_files', []))}")
    
    # Получение информации о пользователе
    user_info = await get_user(str(user.id))
    phone = obj.get('phone_number', '')
    if not phone and user_info:
        phone = user_info.get('phone_number', '')
    
    # Проверяем наличие контактов (телефон или username)
    show_username = obj.get('show_username', False)
    has_username = show_username and user_info and user_info.get('username')
    
    if not phone and not has_username:
        # Нет ни телефона, ни username - нельзя публиковать
        error_text = "❌ <b>Невозможно опубликовать</b>\n\n"
        error_text += "С вами не смогут связаться, так как не указан номер телефона и не включен ник Telegram.\n\n"
        error_text += "Пожалуйста, укажите номер телефона или включите отображение ника Telegram в настройках контактов."
        
        keyboard = [
            [InlineKeyboardButton("Настроить контакты", callback_data="set_contacts")],
            [InlineKeyboardButton("Назад к редактированию", callback_data="back_to_preview")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            try:
                await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            except Exception as e:
                try:
                    await query.message.reply_text(error_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
                except Exception as e2:
                    logger.error(f"Error sending error message: {e2}")
        else:
            await update.message.reply_text(error_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        
        return OBJECT_PREVIEW_MENU
    
    # Формирование текста публикации
    publication_text = await format_publication_text(obj, user_info)
    
    # Определение целевых чатов
    target_chats = await get_target_chats_for_object(obj)
    
    # Публикация в чаты с учетом лимитов
    published_count = 0
    media_files = obj.get('media_files', [])
    
    logger.info(f"Starting publication - Object: {object_id}, Media files: {len(media_files)}, Target chats: {len(target_chats)}")
    await log_action("PUBLISH_START", user.id, user.username, f"Object: {object_id}, Media: {len(media_files)}, Chats: {len(target_chats)}")
    
    # Формируем сообщения для очереди
    for chat_id in target_chats:
        logger.info(f"Publishing to chat: {chat_id}, Object: {object_id}, Media count: {len(media_files)}")
        try:
            if media_files:
                # Отправка с медиа
                media_group = []
                parse_mode = get_parse_mode_for_text(publication_text)
                for i, media in enumerate(media_files[:10]):
                    # Caption добавляем только к первому медиа в группе
                    caption = publication_text if i == 0 else None
                    if media['type'] == 'photo':
                        media_group.append(InputMediaPhoto(media['file_id'], caption=caption, parse_mode=parse_mode if caption else None))
                    elif media['type'] == 'video':
                        media_group.append(InputMediaVideo(media['file_id'], caption=caption, parse_mode=parse_mode if caption else None))
                
                # Логирование сформированной media_group
                logger.info(f"PUBLICATION_MEDIA_GROUP_FORMED | Object: {object_id} | "
                            f"Media count: {len(media_group)} | "
                            f"First has caption: {media_group[0].caption is not None if media_group else False}")
                await log_action("PUBLISH_MEDIA_GROUP_FORMED", user.id, user.username, f"Object: {object_id}, Media count: {len(media_group)}, First media has caption: {media_group[0].caption is not None if media_group else False}")
                
                if len(media_group) == 1:
                    # Одно медиа
                    if isinstance(media_group[0], InputMediaPhoto):
                        message_data = {
                            "type": "photo",
                            "photo": media_group[0].media,
                            "caption": publication_text
                        }
                    else:
                        message_data = {
                            "type": "video",
                            "video": media_group[0].media,
                            "caption": publication_text
                        }
                    await log_action("PUBLISH_SINGLE_MEDIA", user.id, user.username, f"Chat: {chat_id}, Object: {object_id}, Media type: {media_group[0].__class__.__name__}")
                    success = await send_publication_with_rate_limit(context, chat_id, message_data)
                    if success:
                        await increment_chat_publications(chat_id)
                        published_count += 1
                        await log_action("OBJECT_PUBLISHED", user.id, user.username, 
                                      f"Chat: {chat_id}, Object: {object_id}")
                    else:
                        logger.error(f"Failed to send single media to chat {chat_id}")
                        await log_action("PUBLICATION_FAILED_SINGLE", user.id, user.username, 
                                      f"Chat: {chat_id}, Object: {object_id}")
                        continue
                else:
                    # Несколько медиа - caption уже добавлен к первому медиа в media_group
                    logger.info(f"PUBLISH_MEDIA_GROUP - Chat: {chat_id}, Object: {object_id}, Media count: {len(media_group)}")
                    logger.debug(f"Media group details - First caption: {media_group[0].caption[:100] if media_group[0].caption else 'None'}..., Parse mode: {media_group[0].parse_mode}")
                    await log_action("PUBLISH_MEDIA_GROUP", user.id, user.username, f"Chat: {chat_id}, Object: {object_id}, Media count: {len(media_group)}")
                    message_data = {
                        "type": "media_group",
                        "media": media_group
                    }
                    success = await send_publication_with_rate_limit(context, chat_id, message_data)
                    if success:
                        logger.info(f"Media group sent successfully to chat: {chat_id}")
                        await increment_chat_publications(chat_id)
                        published_count += 1
                        await log_action("OBJECT_PUBLISHED", user.id, user.username, 
                                      f"Chat: {chat_id}, Object: {object_id}")
                    else:
                        logger.error(f"Failed to send media group to chat {chat_id}")
                        await log_action("PUBLICATION_FAILED_MEDIA_GROUP", user.id, user.username, 
                                      f"Chat: {chat_id}, Object: {object_id}, Media count: {len(media_group)}")
                        continue  # Продолжаем с следующим чатом
            else:
                # Отправка только текста
                message_data = {
                    "type": "text",
                    "text": publication_text
                }
                success = await send_publication_with_rate_limit(context, chat_id, message_data)
                if success:
                    await increment_chat_publications(chat_id)
                    published_count += 1
                    await log_action("OBJECT_PUBLISHED", user.id, user.username, 
                                  f"Chat: {chat_id}, Object: {object_id}")
                else:
                    logger.error(f"Failed to send text to chat {chat_id}")
                    await log_action("PUBLICATION_FAILED_TEXT", user.id, user.username, 
                                  f"Chat: {chat_id}, Object: {object_id}")
                    continue
        except Exception as e:
            logger.error(f"PUBLICATION_EXCEPTION | Chat: {chat_id} | Object: {object_id} | Error: {str(e)}", exc_info=True)
            await log_action("PUBLICATION_ERROR", user.id, user.username, 
                                  f"Chat: {chat_id}, Error: {str(e)}")
            continue  # Продолжаем с следующим чатом, не прерываем весь процесс
    
    # Обновление объекта только если была успешная публикация
    if published_count > 0:
        await update_object(object_id, {
            "status": "опубликовано",
            "publication_date": format_moscow_datetime(),
            "target_chats": target_chats,
            "phone_number": phone,
            "publication_type": "immediate"
        })
        
        # Обновление статистики пользователя только при успешной публикации
        if user_info:
            user_info["total_publications"] = user_info.get("total_publications", 0) + 1
            await save_user(str(user.id), user_info)
    else:
        # Если не было успешных публикаций, обновляем только информацию о чатах
        await update_object(object_id, {
            "target_chats": target_chats,
            "phone_number": phone
        })
    
    # Сообщение пользователю
    keyboard = [[InlineKeyboardButton("🏠 На главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if published_count > 0:
        success_text = PUBLICATION_SUCCESS.format(count=published_count)
        # Отправляем новое сообщение вместо редактирования (так как может быть фото)
        if query:
            await query.message.reply_text(success_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(success_text, reply_markup=reply_markup)
    else:
        error_text = "Объект сохранен, но не опубликован (не найдены подходящие чаты).\n\n"
        error_text += "Возможные причины:\n"
        error_text += "• Чаты еще не настроены администратором\n"
        error_text += "• Нет чатов, соответствующих параметрам объекта (тип комнат, район, цена)"
        # Отправляем новое сообщение вместо редактирования
        if query:
            await query.message.reply_text(error_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(error_text, reply_markup=reply_markup)
    
    # ВАЖНО: оставляем пользователя в меню редактирования и явно фиксируем состояние
    logger.info(f"PUBLICATION_COMPLETED - Object: {object_id}, Published: {published_count}")
    context.user_data["_conversation_state"] = OBJECT_PREVIEW_MENU
    context.user_data["_conversation_name"] = "add_object_handler"
    
    # Возвращаем состояние, чтобы пользователь мог продолжить работу с объектом
    return OBJECT_PREVIEW_MENU


async def edit_object(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование объекта (возврат к началу процесса)"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if user.id not in user_data:
        await query.edit_message_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    # Возврат к выбору типа комнат
    rooms = await get_rooms_config()
    keyboard = [[InlineKeyboardButton(room, callback_data=f"rooms_{room}")] for room in rooms]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(ADD_OBJECT_ROOMS_QUESTION, reply_markup=reply_markup)
    return OBJECT_WAITING_ROOMS


async def cancel_object(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания объекта"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if user.id in user_data:
        object_id = user_data[user.id].get("object_id")
        if object_id:
            await delete_object(object_id)
        del user_data[user.id]
    
    await query.edit_message_text("Создание объекта отменено.")
    await show_main_menu(update, context)
    return ConversationHandler.END


# ==================== Мои объекты ====================

async def my_objects_old(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Показать список объектов пользователя с пагинацией (старая версия)"""
    # Обрабатываем как callback_query, так и обычный вызов
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message = query.message
        
        # Проверяем, не это ли callback для пагинации
        if query.data.startswith("my_objects_page_"):
            page = int(query.data.replace("my_objects_page_", ""))
    else:
        query = None
        message = update.message if update.message else None
    
    user = update.effective_user
    await log_action("MY_OBJECTS_VIEWED", user.id, user.username, f"Page: {page}")
    
    # Обновляем список объектов каждый раз
    objects = await get_user_objects(str(user.id))
    
    if not objects:
        keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if query:
            await query.edit_message_text(NO_OBJECTS, reply_markup=reply_markup)
        elif message:
            await message.reply_text(NO_OBJECTS, reply_markup=reply_markup)
        return
    
    # Пагинация: показываем по 10 объектов на странице
    objects_per_page = 10
    total_pages = (len(objects) + objects_per_page - 1) // objects_per_page
    start_idx = page * objects_per_page
    end_idx = min(start_idx + objects_per_page, len(objects))
    page_objects = objects[start_idx:end_idx]
    
    # Формирование списка объектов с командами
    text = f"<b>{MY_OBJECTS_TITLE}</b>\n"
    if total_pages > 1:
        text += f"<i>Страница {page + 1} из {total_pages}</i>\n"
    text += "\n"
    
    # Формируем клавиатуру с кнопками для каждого объекта
    keyboard = []
    
    for obj in page_objects:
        obj_id = obj['id']
        status = obj.get('status', 'черновик')
        rooms = obj.get('rooms_type', 'Не указано')
        price = obj.get('price', 0)
        districts = obj.get('districts', [])
        address = obj.get('address', '')
        publication_date = obj.get('publication_date', '')
        
        # Формируем строку с информацией об объекте
        obj_text = f"<b>• {rooms}</b> | <b>{price}</b> тыс. руб.\n"
        
        # Добавляем район, если есть
        if districts:
            districts_str = ", ".join(districts)
            obj_text += f"📍 <b>Район:</b> {districts_str}\n"
        
        # Добавляем улицу, если есть
        if address:
            obj_text += f"{address}\n"
        
        # Показываем статус "опубликовано" только если объект действительно опубликован
        # (статус "опубликовано" И есть дата публикации)
        if status == "опубликовано" and publication_date:
            # Форматируем дату публикации
            try:
                pub_date = parse_moscow_datetime(publication_date, "%Y-%m-%d %H:%M:%S")
                formatted_date = format_moscow_datetime(pub_date, "%d.%m.%Y %H:%M")
                obj_text += f"✅ <b>Опубликовано:</b> {formatted_date}\n"
            except:
                obj_text += f"✅ <b>Опубликовано:</b> {publication_date}\n"
        elif status == "запланировано":
            obj_text += f"⏰ <b>Запланировано</b>\n"
        else:
            obj_text += f"📝 <b>Черновик</b>\n"
        
        text += obj_text
        # Убираем префикс obj_ из obj_id, так как он уже есть в команде
        obj_id_clean = obj_id.replace("obj_", "") if obj_id.startswith("obj_") else obj_id
        text += f" Редактировать: /edit_obj_{obj_id_clean}\n"
        text += f" Удалить: /delete_obj_{obj_id_clean}\n\n"
    
    # Формируем клавиатуру только с навигацией
    keyboard = []
    
    # Кнопки навигации по страницам
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"my_objects_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"my_objects_page_{page + 1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    elif message:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def my_objects(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Показать список объектов пользователя с новым меню"""
    # Обрабатываем как callback_query, так и обычный вызов
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message = query.message
        
        # Проверяем, не это ли callback для пагинации
        if query.data.startswith("my_objects_page_"):
            page = int(query.data.replace("my_objects_page_", ""))
        elif query.data.startswith("edit_object_from_list_"):
            # Обработка нажатия на объект - открываем редактирование
            await edit_object_from_list(update, context)
            return
    else:
        query = None
        message = update.message if update.message else None
    
    user = update.effective_user
    await log_action("MY_OBJECTS_VIEWED", user.id, user.username, f"Page: {page}")
    # Фиксируем, что последнее меню сортировки - мои объекты
    context.user_data["last_sort_menu"] = "my_objects"
    
    # Получаем объекты пользователя
    objects = await get_user_objects(str(user.id))
    
    # Получаем порядок сортировки
    sort_order = await get_user_sort_order(str(user.id))
    
    # Сортируем объекты
    if sort_order == "new":
        # Сначала новые (по дате создания, новые сверху)
        objects.sort(key=lambda x: x.get("creation_date", ""), reverse=True)
    else:
        # Сначала старые (по дате создания, старые сверху)
        objects.sort(key=lambda x: x.get("creation_date", ""), reverse=False)
    
    # Получаем дату последней автопубликации
    last_autopublish = await get_user_last_autopublish_date(str(user.id))
    
    # Формируем текст сообщения
    text = f"<b>{MY_OBJECTS_TITLE}</b>\n\n"
    text += f"Количество объектов: <b>{len(objects)}</b>\n"
    text += "\n"
    text += "Сортировка объектов:\n"
    text += "• /sort_new — сначала новые\n"
    text += "• /sort_old — сначала старые\n"
    text += "После ввода команды вернемся в это меню.\n\n"
    text += "Команда для удаления всех объектов: /delete_all\n"
    
    if last_autopublish:
        try:
            last_dt = parse_moscow_datetime(last_autopublish, "%Y-%m-%d %H:%M:%S")
            formatted_date = format_moscow_datetime(last_dt, "%d.%m.%Y %H:%M")
            text += f"Дата последней автопубликации: <b>{formatted_date}</b>\n"
        except:
            text += f"Дата последней автопубликации: <b>{last_autopublish}</b>\n"
    else:
        text += "Дата последней автопубликации: <i>нет данных</i>\n"
    
    text += "\n"
    
    if sort_order == "new":
        text += "Сортировка: сначала новые (/sort_old - сначала старые)\n"
    else:
        text += "Сортировка: сначала старые (/sort_new - сначала новые)\n"
    
    if not objects:
        keyboard = [[InlineKeyboardButton("🏠 На главную", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if query:
            await query.edit_message_text(text + "\n" + NO_OBJECTS, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        elif message:
            await message.reply_text(text + "\n" + NO_OBJECTS, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return
    
    # Пагинация: показываем по 10 объектов на странице
    objects_per_page = 10
    total_pages = (len(objects) + objects_per_page - 1) // objects_per_page
    start_idx = page * objects_per_page
    end_idx = min(start_idx + objects_per_page, len(objects))
    page_objects = objects[start_idx:end_idx]
    
    # Формируем клавиатуру с кнопками для каждого объекта
    keyboard = []
    
    for obj in page_objects:
        obj_id = obj['id']
        price = obj.get('price', 0)
        rooms = obj.get('rooms_type', '')
        districts = obj.get('districts', [])
        
        # Формируем текст кнопки: "3500 | 1к | Прикубанский | 666"
        button_text = f"{price}"
        if rooms:
            # Убираем лишние символы из типа комнат для краткости
            rooms_short = rooms.replace(" комнат", "к").replace(" комната", "к").replace(" комнаты", "к")
            button_text += f" | {rooms_short}"
        if districts:
            # Берем первый выбранный район
            button_text += f" | {districts[0]}"
        button_text += f" | {obj_id}"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"edit_object_from_list_{obj_id}")])
    
    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"my_objects_page_{page - 1}"))
    nav_buttons.append(InlineKeyboardButton("🏠 На главную", callback_data="back_to_menu"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"my_objects_page_{page + 1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    elif message:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def sort_new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для переключения сортировки на 'сначала новые'"""
    user = update.effective_user
    await set_user_sort_order(str(user.id), "new")
    await log_action("SORT_ORDER_CHANGED", user.id, user.username, "new")
    # Определяем, в каком меню был пользователь
    last_menu = context.user_data.get("last_sort_menu", "my_objects")
    if last_menu == "auto_publish":
        await auto_publish_settings(update, context)
    else:
        await my_objects(update, context, page=0)


async def sort_old_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для переключения сортировки на 'сначала старые'"""
    user = update.effective_user
    await set_user_sort_order(str(user.id), "old")
    await log_action("SORT_ORDER_CHANGED", user.id, user.username, "old")
    # Определяем, в каком меню был пользователь
    last_menu = context.user_data.get("last_sort_menu", "my_objects")
    if last_menu == "auto_publish":
        await auto_publish_settings(update, context)
    else:
        await my_objects(update, context, page=0)


async def delete_all_objects_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для запроса удаления всех объектов пользователя"""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить все", callback_data="confirm_delete_all_yes")],
        [InlineKeyboardButton("❌ Отмена", callback_data="confirm_delete_all_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "Вы уверены, что хотите удалить все ваши объекты?\n"
        "Действие необратимо."
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)


async def confirm_delete_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления всех объектов пользователя"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if query.data == "confirm_delete_all_no":
        await query.edit_message_text("Удаление отменено.")
        return
    
    objects = await load_json("objects.json")
    removed = 0
    for obj_id in list(objects.keys()):
        if objects[obj_id].get("user_id") == str(user.id):
            del objects[obj_id]
            removed += 1
    await save_json("objects.json", objects)
    
    # Очищаем временные данные, если пользователь что-то редактировал
    if user.id in user_data:
        user_data.pop(user.id, None)
    
    keyboard = [[InlineKeyboardButton("🏠 На главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Удалено объектов: {removed}", reply_markup=reply_markup)


async def view_object(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр детальной информации об объекте"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("view_object_", "")
    obj = await get_object(object_id)
    
    if not obj:
        await query.edit_message_text("Объект не найден.")
        return
    
    # Формирование текста
    text = f"<b>{OBJECT_INFO}</b>\n\n"
    text += f"<b>ID:</b> {object_id}\n"
    text += f"<b>{OBJECT_PREVIEW_ROOMS}:</b> {obj.get('rooms_type', 'Не указано')}\n"
    text += f"<b>{OBJECT_PREVIEW_PRICE}:</b> {obj.get('price', 0)} тыс. руб.\n"
    
    districts = obj.get('districts', [])
    if districts:
        text += f"<b>{OBJECT_PREVIEW_DISTRICTS}:</b> {', '.join(districts)}\n"
    
    caption = obj.get('caption', '')
    if caption:
        text += f"\n<b>{OBJECT_PREVIEW_CAPTION}:</b>\n{caption}\n"
    
    phone = obj.get('phone_number', '')
    if phone:
        text += f"\n<b>{OBJECT_PREVIEW_PHONE}:</b> {phone}\n"
    
    status = obj.get('status', 'черновик')
    text += f"\n<b>Статус:</b> {status}\n"
    
    if status == "опубликовано":
        pub_date = obj.get('publication_date', '')
        if pub_date:
            text += f"<b>Дата публикации:</b> {pub_date}\n"
    
    # Кнопки
    keyboard = []
    if status == "черновик":
        keyboard.append([InlineKeyboardButton("Опубликовать", callback_data=f"publish_draft_{object_id}")])
        keyboard.append([InlineKeyboardButton(BUTTON_DELETE, callback_data=f"delete_object_{object_id}")])
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="my_objects")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправка медиа, если есть
    media_files = obj.get('media_files', [])
    if media_files:
        try:
            media_group = []
            for media in media_files[:10]:
                if media['type'] == 'photo':
                    media_group.append(InputMediaPhoto(media['file_id']))
                elif media['type'] == 'video':
                    media_group.append(InputMediaVideo(media['file_id']))
            
            if len(media_group) == 1:
                # Проверяем тип через isinstance, так как media_type не существует
                if isinstance(media_group[0], InputMediaPhoto):
                    await query.message.reply_photo(
                        photo=media_group[0].media,
                        caption=text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await query.message.reply_video(
                        video=media_group[0].media,
                        caption=text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
            else:
                await query.message.reply_media_group(media=media_group)
                await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        except Exception as e:
            await log_action("VIEW_OBJECT_MEDIA_ERROR", update.effective_user.id, 
                                   update.effective_user.username, str(e))
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def delete_object_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /delete_obj_ID для удаления объекта"""
    # Проверка, что сообщение из личного чата
    if not await is_private_chat(update):
        return
    
    user = update.effective_user
    command_text = update.message.text.strip()
    
    await log_action("DELETE_COMMAND_RECEIVED", user.id, user.username, f"Command: {command_text}")
    
    # Извлекаем object_id из команды /delete_obj_xxxxxx
    if command_text.startswith("/delete_obj_"):
        object_id = command_text.replace("/delete_obj_", "").strip()
        # Убираем лишний префикс obj_ если он есть (на случай /delete_obj_obj_...)
        if object_id.startswith("obj_"):
            object_id = object_id
        else:
            object_id = f"obj_{object_id}"
    else:
        await log_action("DELETE_COMMAND_INVALID_FORMAT", user.id, user.username, f"Command: {command_text}")
        await update.message.reply_text("Используйте команду в формате: /delete_obj_xxxxxx")
        return
    
    # Проверяем, что объект существует и принадлежит пользователю
    obj = await get_object(object_id)
    if not obj:
        await log_action("DELETE_COMMAND_OBJECT_NOT_FOUND", user.id, user.username, f"Object ID: {object_id}")
        await update.message.reply_text("Объект не найден.")
        return
    
    if obj.get('user_id') != str(user.id):
        await log_action("DELETE_COMMAND_ACCESS_DENIED", user.id, user.username, f"Object ID: {object_id}")
        await update.message.reply_text("Вы можете удалять только свои объекты.")
        return
    
    # Подтверждение удаления
    rooms = obj.get('rooms_type', 'Не указано')
    price = obj.get('price', 0)
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{object_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data="my_objects")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚠️ <b>Подтвердите удаление объекта:</b>\n\n"
        f"• {rooms} | {price} тыс. руб.\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def delete_object_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление объекта через callback (старый способ, оставлен для совместимости)"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("delete_object_", "")
    obj = await get_object(object_id)
    
    if not obj:
        await query.answer("Объект не найден.", show_alert=True)
        return
    
    # Проверяем, что объект принадлежит пользователю
    user = update.effective_user
    if obj.get('user_id') != str(user.id):
        await query.answer("Вы можете удалять только свои объекты.", show_alert=True)
        return
    
    # Подтверждение удаления
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{object_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data="my_objects")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    rooms = obj.get('rooms_type', 'Не указано')
    price = obj.get('price', 0)
    
    await query.edit_message_text(
        f"⚠️ <b>Подтвердите удаление объекта:</b>\n\n"
        f"• {rooms} | {price} тыс. руб.\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def confirm_delete_object(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления объекта"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("confirm_delete_", "")
    obj = await get_object(object_id)
    
    if not obj:
        await query.answer("Объект не найден.", show_alert=True)
        return
    
    # Проверяем, что объект принадлежит пользователю
    user = update.effective_user
    if obj.get('user_id') != str(user.id):
        await query.answer("Вы можете удалять только свои объекты.", show_alert=True)
        return
    
    # Удаляем объект
    await delete_object(object_id)
    await log_action("OBJECT_DELETED", user.id, user.username, f"Object: {object_id}")
    
    # Возвращаемся к списку объектов
    await my_objects(update, context)


async def publish_draft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Публикация черновика"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("publish_draft_", "")
    
    # Сохранение object_id во временные данные для функции публикации
    user = update.effective_user
    user_data[user.id] = {"object_id": object_id}
    
    # Используем меню выбора времени публикации
    await show_publication_time_menu(update, context)


# ==================== Настройки ====================

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать настройки"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await log_action("SETTINGS_OPENED", user.id, user.username)
    
    user_info = await get_user(str(user.id))
    default_show_username = user_info.get("default_show_username", False) if user_info else False
    show_footer = user_info.get("show_footer", False) if user_info else False
    
    # Формируем текст с данными по умолчанию
    settings_text = f"{SETTINGS_TITLE}\n\n"
    settings_text += "<b>Данные по умолчанию:</b>\n"
    
    contact_name = user_info.get("contact_name", "") if user_info else ""
    phone = user_info.get("phone_number", "") if user_info else ""
    username = user.username if user.username else ""
    
    if contact_name:
        settings_text += f"Имя: {contact_name}\n"
    else:
        settings_text += "Имя: не указано\n"
    
    if phone:
        settings_text += f"Номер телефона: {phone}\n"
    else:
        settings_text += "Номер телефона: не указан\n"
    
    if default_show_username and username:
        settings_text += f"Ник TG: @{username}\n"
    else:
        settings_text += "Ник TG: отключен\n"
    
    keyboard = [
        [
            InlineKeyboardButton("Добавить номер телефона", callback_data="settings_add_phone"),
            InlineKeyboardButton("Указать имя", callback_data="settings_set_name")
        ],
        [InlineKeyboardButton("Изменить номер телефона", callback_data="settings_change_phone")],
        [InlineKeyboardButton(f"Указывать ник TG по умолчанию: {'✅' if default_show_username else '❌'}", 
                             callback_data="settings_toggle_default_username")],
        [InlineKeyboardButton(f"Публикация с футером: {'✅' if show_footer else '❌'}", 
                             callback_data="settings_toggle_footer")],
        [InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def settings_add_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс добавления номера телефона"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(SETTINGS_PHONE_ADD)
    return SETTINGS_WAITING_PHONE


async def settings_change_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс изменения номера телефона"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(SETTINGS_PHONE_CHANGE)
    return SETTINGS_WAITING_PHONE


async def settings_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода номера телефона"""
    user = update.effective_user
    phone = update.message.text.strip()
    
    # Простая валидация номера
    if not phone or len(phone) < 10:
        text = "Некорректный номер телефона. Попробуйте еще раз.\n\n"
        text += "Номер в формате:\n"
        text += "89693386969"
        await update.message.reply_text(text)
        return SETTINGS_WAITING_PHONE
    
    # Сохранение номера
    user_info = await get_user(str(user.id))
    if not user_info:
        user_info = {}
    
    user_info["phone_number"] = phone
    await save_user(str(user.id), user_info)
    
    await log_action("PHONE_UPDATED", user.id, user.username, f"Phone: {phone}")
    
    await update.message.reply_text(SETTINGS_PHONE_SAVED)
    await show_main_menu(update, context)
    return ConversationHandler.END


async def settings_set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс указания имени"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await log_action("SETTINGS_SET_NAME_CLICKED", user.id, user.username)
    
    await query.edit_message_text("Введите ваше имя:")
    return SETTINGS_WAITING_NAME


async def settings_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода имени"""
    user = update.effective_user
    name = update.message.text.strip()
    
    user_info = await get_user(str(user.id))
    if not user_info:
        user_info = {}
    
    user_info["contact_name"] = name
    await save_user(str(user.id), user_info)
    
    await log_action("USER_NAME_SET", user.id, user.username, f"Name: {name}")
    
    await update.message.reply_text(f"Имя '{name}' сохранено.")
    await show_main_menu(update, context)
    return ConversationHandler.END


async def settings_toggle_default_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключить показ username по умолчанию"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await log_action("SETTINGS_TOGGLE_USERNAME_CLICKED", user.id, user.username)
    
    user_info = await get_user(str(user.id))
    if not user_info:
        user_info = {}
    
    current_value = user_info.get("default_show_username", False)
    user_info["default_show_username"] = not current_value
    await save_user(str(user.id), user_info)
    
    await log_action("USER_DEFAULT_USERNAME_TOGGLED", user.id, user.username, 
                     f"New value: {not current_value}")
    
    await settings(update, context)


async def settings_toggle_footer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключить показ футера в публикациях"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Проверяем роль пользователя
    user_role = await get_user_role(str(user.id))
    if user_role not in [ROLE_PREMIUM, ROLE_PROTIME]:
        await query.answer("Эта настройка доступна только для Premium и Pro Time пользователей.", show_alert=True)
        return
    
    await log_action("SETTINGS_TOGGLE_FOOTER_CLICKED", user.id, user.username)
    
    user_info = await get_user(str(user.id))
    if not user_info:
        user_info = {}
    
    current_value = user_info.get("show_footer", False)
    user_info["show_footer"] = not current_value
    await save_user(str(user.id), user_info)
    
    await log_action("USER_FOOTER_TOGGLED", user.id, user.username, 
                     f"New value: {not current_value}")
    
    await settings(update, context)


async def settings_profile_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о профиле"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_info = await get_user(str(user.id))
    
    text = f"<b>{SETTINGS_PROFILE_INFO}</b>\n\n"
    text += f"<b>ID:</b> {user.id}\n"
    text += f"<b>Username:</b> @{user.username if user.username else 'не указан'}\n"
    
    if user_info:
        text += f"<b>Имя:</b> {user_info.get('contact_name', 'не указано')}\n"
        text += f"<b>Телефон:</b> {user_info.get('phone_number', 'не указан')}\n"
        text += f"<b>Указывать ник TG по умолчанию:</b> {'Да' if user_info.get('default_show_username', False) else 'Нет'}\n"
        text += f"<b>Первый визит:</b> {user_info.get('first_seen', 'неизвестно')}\n"
        text += f"<b>Последняя активность:</b> {user_info.get('last_activity', 'неизвестно')}\n"
        text += f"<b>Всего публикаций:</b> {user_info.get('total_publications', 0)}\n"
    
    keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="settings")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


# ==================== Другие функции ====================

async def all_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход к папке со всеми чатами"""
    query = update.callback_query
    await query.answer()
    
    # Открываем ссылку на папку с чатами
    keyboard = [
        [InlineKeyboardButton("📁 Открыть папку с чатами", url="https://t.me/addlist/QDGm9RwOldE4YzM6")],
        [InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "Нажмите на кнопку ниже, чтобы открыть папку со всеми чатами:"
    await query.edit_message_text(text, reply_markup=reply_markup)


async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Связь с админом"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💬 Написать админу", url="https://t.me/bochkarev_t")],
        [InlineKeyboardButton(BUTTON_BACK, callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "Нажмите на кнопку ниже, чтобы написать администратору:"
    await query.edit_message_text(text, reply_markup=reply_markup)


# ==================== Админ-панель ====================

async def admin_chat_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список чатов с подробной информацией"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    chats = await get_chats()
    
    if not chats:
        keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Чаты не найдены.", reply_markup=reply_markup)
        return
    
    text = f"<b>{ADMIN_CHAT_LIST}</b>\n\n"
    
    for chat_id, chat_data in chats.items():
        title = chat_data.get('title', 'Без названия')
        chat_type = chat_data.get('type', 'неизвестно')
        params = chat_data.get('params', '')
        publications = chat_data.get('total_publications', 0)
        added_date = chat_data.get('added_date', 'неизвестно')
        
        # Получение username чата, если возможно
        username = "N/A"
        try:
            chat_info = await context.bot.get_chat(chat_id)
            if chat_info.username:
                username = f"@{chat_info.username}"
        except:
            pass
        
        text += f"<b>{title}</b>\n"
        text += f"ID: <code>{chat_id}</code>\n"
        text += f"Username: {username}\n"
        text += f"Тип: {chat_type}\n"
        
        # Форматирование параметров в зависимости от типа
        if chat_type == "price_range":
            if isinstance(params, list) and len(params) == 2:
                text += f"Диапазон: {params[0]}-{params[1]} тыс. руб.\n"
            else:
                text += f"Параметры: {params}\n"
        elif chat_type == "rooms":
            text += f"Тип комнат: {params}\n"
        elif chat_type == "district":
            text += f"Район: {params}\n"
        else:
            text += f"Параметры: {params}\n"
        
        text += f"Публикаций: {publications}\n"
        text += f"Добавлен: {added_date}\n"
        text += f"Команда удаления: <code>/Delete_Chat_{chat_id}</code>\n\n"
    
    keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    await log_action("ADMIN_CHAT_LIST_VIEWED", update.effective_user.id, 
                     update.effective_user.username)


async def admin_add_chat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса добавления чата"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    await query.edit_message_text(ADMIN_ADD_CHAT_ID)
    return ADMIN_WAITING_CHAT_ID


async def admin_chat_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода chat_id"""
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        return ConversationHandler.END
    
    chat_id_text = update.message.text.strip()
    
    # Попытка получить chat_id из username или числового ID
    try:
        if chat_id_text.startswith('@'):
            chat = await context.bot.get_chat(chat_id_text)
            chat_id = str(chat.id)
        else:
            chat_id = str(int(chat_id_text))
    except Exception as e:
        await update.message.reply_text(f"Ошибка: не удалось получить информацию о чате. {str(e)}")
        return ADMIN_WAITING_CHAT_ID
    
    # Сохранение chat_id во временные данные
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["admin_chat_id"] = chat_id
    
    await update.message.reply_text(ADMIN_ADD_CHAT_TITLE)
    return ADMIN_WAITING_CHAT_TITLE


async def admin_chat_title_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода названия чата"""
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        return ConversationHandler.END
    
    title = update.message.text.strip()
    
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["admin_chat_title"] = title
    
    # Выбор типа чата
    keyboard = [
        [InlineKeyboardButton("price_range", callback_data="chat_type_price_range")],
        [InlineKeyboardButton("rooms", callback_data="chat_type_rooms")],
        [InlineKeyboardButton("district", callback_data="chat_type_district")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(ADMIN_ADD_CHAT_TYPE, reply_markup=reply_markup)
    return ADMIN_WAITING_CHAT_TYPE


async def admin_chat_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора типа чата"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        return ConversationHandler.END
    
    chat_type = query.data.replace("chat_type_", "")
    
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["admin_chat_type"] = chat_type
    
    # Выбор параметров в зависимости от типа
    if chat_type == "price_range":
        price_ranges = await get_price_ranges()
        keyboard = []
        for range_name in price_ranges.keys():
            keyboard.append([InlineKeyboardButton(range_name, callback_data=f"chat_param_{range_name}")])
        keyboard.append([InlineKeyboardButton("Создать новый диапазон", callback_data="chat_param_new")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(ADMIN_ADD_CHAT_PARAMS, reply_markup=reply_markup)
        return ADMIN_WAITING_CHAT_PARAMS
        
    elif chat_type == "rooms":
        rooms = await get_rooms_config()
        keyboard = [[InlineKeyboardButton(room, callback_data=f"chat_param_{room}")] for room in rooms]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(ADMIN_ADD_CHAT_PARAMS, reply_markup=reply_markup)
        return ADMIN_WAITING_CHAT_PARAMS
        
    elif chat_type == "district":
        districts_config = await get_districts_config()
        districts = list(districts_config.keys())
        
        keyboard = []
        # Кнопки существующих районов
        if districts:
            for district in districts:
                keyboard.append([InlineKeyboardButton(district, callback_data=f"chat_param_{district}")])
        else:
            # Если районов нет, показываем сообщение
            pass
        
        # Кнопка для создания нового района
        keyboard.append([InlineKeyboardButton("➕ Создать новый район", callback_data="chat_param_new_district")])
        keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="admin_back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "Выберите район:\n\n"
        if districts:
            text += "Или отправьте название нового района, чтобы создать его и привязать к чату."
        else:
            text += "Районов пока нет. Отправьте название нового района, чтобы создать его и привязать к чату."
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_WAITING_CHAT_PARAMS


async def admin_chat_params_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора параметров чата"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        return ConversationHandler.END
    
    param_data = query.data.replace("chat_param_", "")
    chat_type = user_data[user.id].get("admin_chat_type")
    
    if param_data == "new" and chat_type == "price_range":
        await query.edit_message_text("Введите новый диапазон в формате: название|мин|макс (например: 10000-15000|10000|15000)")
        return ADMIN_WAITING_CHAT_PARAMS
    
    if param_data == "new_district" and chat_type == "district":
        await query.edit_message_text("Введите название нового района:")
        # Сохраняем флаг, что это новый район
        if user.id not in user_data:
            user_data[user.id] = {}
        user_data[user.id]["admin_new_district"] = True
        return ADMIN_WAITING_CHAT_PARAMS
    
    # Определение параметров
    if chat_type == "price_range":
        if param_data == "new":
            # Обработка будет в следующем сообщении
            return ADMIN_WAITING_CHAT_PARAMS
        else:
            price_ranges = await get_price_ranges()
            params = price_ranges.get(param_data, [0, 0])
    elif chat_type == "rooms":
        params = param_data
    elif chat_type == "district":
        params = param_data
    else:
        params = param_data
    
    # Сохранение чата
    chat_id = user_data[user.id].get("admin_chat_id")
    title = user_data[user.id].get("admin_chat_title")
    
    chat_data = {
        "title": title,
        "type": chat_type,
        "params": params,
        "added_date": format_moscow_datetime(format_str="%Y-%m-%d"),
        "total_publications": 0
    }
    
    await add_chat(chat_id, chat_data)
    await log_action("CHAT_ADDED", user.id, user.username, f"Chat: {chat_id}, Type: {chat_type}")
    
    await query.edit_message_text(ADMIN_CHAT_ADDED)
    
    # Очистка временных данных
    if user.id in user_data:
        del user_data[user.id]
    
    await show_admin_panel(update, context)
    return ConversationHandler.END


async def admin_chat_params_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода параметров чата (для нового ценового диапазона или нового района)"""
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        return ConversationHandler.END
    
    chat_type = user_data[user.id].get("admin_chat_type")
    is_new_district = user_data[user.id].get("admin_new_district", False)
    
    # Обработка района (нового или существующего через ввод текста)
    if chat_type == "district":
        district_name = update.message.text.strip()
        
        if not district_name:
            await update.message.reply_text("Название района не может быть пустым.")
            return ADMIN_WAITING_CHAT_PARAMS
        
        # Добавляем район в конфигурацию, если его еще нет
        districts_config = await get_districts_config()
        if district_name not in districts_config:
            districts_config[district_name] = []
            await save_districts_config(districts_config)
            await log_action("DISTRICT_ADDED", user.id, user.username, f"District: {district_name}")
        
        # Используем название района как параметр
        params = district_name
        
        # Сохранение чата
        chat_id = user_data[user.id].get("admin_chat_id")
        title = user_data[user.id].get("admin_chat_title")
        
        chat_data = {
            "title": title,
            "type": chat_type,
            "params": params,
            "added_date": format_moscow_datetime(format_str="%Y-%m-%d"),
            "total_publications": 0
        }
        
        await add_chat(chat_id, chat_data)
        await log_action("CHAT_ADDED", user.id, user.username, f"Chat: {chat_id}, Type: {chat_type}, District: {district_name}")
        
        await update.message.reply_text(ADMIN_CHAT_ADDED)
        
        # Очистка временных данных
        if user.id in user_data:
            del user_data[user.id]
        
        await show_admin_panel(update, context)
        return ConversationHandler.END
    
    # Обработка нового ценового диапазона
    if chat_type == "price_range":
        try:
            # Формат: название|мин|макс
            parts = update.message.text.split('|')
            if len(parts) == 3:
                range_name = parts[0].strip()
                min_price = float(parts[1].strip())
                max_price = float(parts[2].strip())
                
                # Сохранение нового диапазона
                price_ranges = await get_price_ranges()
                price_ranges[range_name] = [min_price, max_price]
                await save_price_ranges(price_ranges)
                
                # Использование нового диапазона как параметра
                params = [min_price, max_price]
                
                # Сохранение чата
                chat_id = user_data[user.id].get("admin_chat_id")
                title = user_data[user.id].get("admin_chat_title")
                
                chat_data = {
                    "title": title,
                    "type": chat_type,
                    "params": params,
                    "added_date": format_moscow_datetime(format_str="%Y-%m-%d"),
                    "total_publications": 0
                }
                
                await add_chat(chat_id, chat_data)
                await log_action("CHAT_ADDED", user.id, user.username, f"Chat: {chat_id}, Type: {chat_type}")
                
                await update.message.reply_text(ADMIN_CHAT_ADDED)
                
                # Очистка временных данных
                if user.id in user_data:
                    del user_data[user.id]
                
                await show_admin_panel(update, context)
                return ConversationHandler.END
            else:
                await update.message.reply_text("Неверный формат. Используйте: название|мин|макс")
                return ADMIN_WAITING_CHAT_PARAMS
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {str(e)}")
            return ADMIN_WAITING_CHAT_PARAMS
    
    # Если тип не распознан, возвращаем ошибку
    await update.message.reply_text("Ошибка: неизвестный тип чата.")
    return ConversationHandler.END


async def admin_districts_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка районов"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    districts_config = await get_districts_config()
    
    text = "<b>Настройки районов</b>\n\n"
    text += "Текущие районы:\n"
    for district, parents in districts_config.items():
        text += f"• {district}"
        if parents:
            text += f" (родители: {', '.join(parents)})"
        text += "\n"
    
    keyboard = [
        [InlineKeyboardButton("Добавить район", callback_data="admin_add_district")],
        [InlineKeyboardButton("Удалить район", callback_data="admin_delete_district")],
        [InlineKeyboardButton("Назначить родителя", callback_data="admin_set_parent")],
        [InlineKeyboardButton(BUTTON_BACK, callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def admin_price_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка ценовых диапазонов"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    price_ranges = await get_price_ranges()
    
    text = "<b>Настройки ценовых диапазонов</b>\n\n"
    text += "Текущие диапазоны:\n"
    for range_name, range_values in price_ranges.items():
        text += f"• {range_name}: {range_values[0]}-{range_values[1]}\n"
    
    keyboard = [
        [InlineKeyboardButton("Добавить диапазон", callback_data="admin_add_price_range")],
        [InlineKeyboardButton("Удалить диапазон", callback_data="admin_delete_price_range")],
        [InlineKeyboardButton(BUTTON_BACK, callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def admin_rooms_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка типов комнат"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    rooms = await get_rooms_config()
    
    text = "<b>Настройки типов комнат</b>\n\n"
    text += "Текущие типы:\n"
    for room in rooms:
        text += f"• {room}\n"
    
    keyboard = [
        [InlineKeyboardButton("Добавить тип", callback_data="admin_add_room")],
        [InlineKeyboardButton("Удалить тип", callback_data="admin_delete_room")],
        [InlineKeyboardButton(BUTTON_BACK, callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def admin_hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню управления хэштегами"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    suffix = await get_hashtag_suffix()
    
    # Собираем все хэштеги
    districts_config = await get_districts_config()
    rooms_config = await get_rooms_config()
    price_ranges = await get_price_ranges()
    
    text = "<b>Управление хэштегами</b>\n\n"
    text += f"<b>Текущий суффикс:</b> {suffix}\n\n"
    
    text += "<b>Хэштеги районов:</b>\n"
    for district in districts_config.keys():
        hashtag = generate_district_hashtag(district, suffix)
        text += f"{hashtag} - {district}\n"
    
    text += "\n<b>Хэштеги комнат:</b>\n"
    for room in rooms_config:
        hashtag = generate_room_hashtag(room, suffix)
        text += f"{hashtag} - {room}\n"
    
    text += "\n<b>Хэштеги ценовых диапазонов:</b>\n"
    for range_name in price_ranges.keys():
        hashtag = generate_price_range_hashtag(range_name, suffix)
        text += f"{hashtag} - {range_name}\n"
    
    keyboard = [
        [InlineKeyboardButton("Изменить суффикс", callback_data="admin_change_hashtag_suffix")],
        [InlineKeyboardButton(BUTTON_BACK, callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def admin_change_hashtag_suffix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать изменение суффикса хэштегов"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    user = update.effective_user
    current_suffix = await get_hashtag_suffix()
    text = f"<b>Изменение суффикса хэштегов</b>\n\n"
    text += f"Текущий суффикс: <code>{current_suffix}</code>\n\n"
    text += "Введите новый суффикс (например: _ф, _кк, _ключи)\n"
    text += "Суффикс должен начинаться с подчеркивания."
    
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["admin_action"] = "change_hashtag_suffix"
    
    keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="admin_hashtags")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return ADMIN_EDITING_HASHTAG_SUFFIX


async def admin_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    # Подсчет статистики
    async with aiofiles.open("users.json", 'r', encoding='utf-8') as f:
        users_content = await f.read()
        users = json.loads(users_content) if users_content.strip() else {}
    async with aiofiles.open("objects.json", 'r', encoding='utf-8') as f:
        objects_content = await f.read()
        objects = json.loads(objects_content) if objects_content.strip() else {}
    chats = await get_chats()
    
    # Статистика пользователей
    total_users = len(users)
    
    # Активные пользователи за периоды
    now = get_moscow_time()
    today = format_moscow_datetime(now, "%Y-%m-%d")
    week_ago = format_moscow_datetime(now - timedelta(days=7), "%Y-%m-%d")
    month_ago = format_moscow_datetime(now - timedelta(days=30), "%Y-%m-%d")
    
    active_day = 0
    active_week = 0
    active_month = 0
    
    for user_data in users.values():
        active_periods = user_data.get("active_periods", {})
        if today in active_periods.get("day", []):
            active_day += 1
        if any(d >= week_ago for d in active_periods.get("week", [])):
            active_week += 1
        if any(d >= month_ago for d in active_periods.get("month", [])):
            active_month += 1
    
    # Новые пользователи
    new_users_day = 0
    new_users_week = 0
    new_users_month = 0
    
    for user_data in users.values():
        first_seen = user_data.get("first_seen", "")
        if first_seen >= today:
            new_users_day += 1
        if first_seen >= week_ago:
            new_users_week += 1
        if first_seen >= month_ago:
            new_users_month += 1
    
    # Статистика публикаций
    total_publications = sum(1 for obj in objects.values() if obj.get("status") == "опубликовано")
    
    pub_day = 0
    pub_week = 0
    pub_month = 0
    
    for obj in objects.values():
        if obj.get("status") == "опубликовано":
            pub_date = obj.get("publication_date", "")
            if pub_date >= today:
                pub_day += 1
            if pub_date >= week_ago:
                pub_week += 1
            if pub_date >= month_ago:
                pub_month += 1
    
    # Публикации по чатам
    publications_by_chat = {}
    for chat_id, chat_data in chats.items():
        publications_by_chat[chat_data.get("title", chat_id)] = chat_data.get("total_publications", 0)
    
    # Формирование текста статистики
    text = f"<b>{STATISTICS_TITLE}</b>\n\n"
    text += f"<b>{STATISTICS_USERS_TOTAL}:</b> {total_users}\n"
    text += f"<b>{STATISTICS_USERS_ACTIVE}:</b> Месяц: {active_month}, Неделя: {active_week}, День: {active_day}\n"
    text += f"<b>{STATISTICS_USERS_NEW}:</b> Месяц: {new_users_month}, Неделя: {new_users_week}, День: {new_users_day}\n\n"
    text += f"<b>{STATISTICS_PUBLICATIONS_TOTAL}:</b> {total_publications}\n"
    text += f"<b>{STATISTICS_PUBLICATIONS_PERIOD}:</b> Месяц: {pub_month}, Неделя: {pub_week}, День: {pub_day}\n\n"
    text += f"<b>{STATISTICS_PUBLICATIONS_BY_CHAT}:</b>\n"
    for chat_name, count in sorted(publications_by_chat.items(), key=lambda x: x[1], reverse=True):
        text += f"• {chat_name}: {count}\n"
    
    keyboard = [
        [InlineKeyboardButton("📋 Новые пользователи за неделю", callback_data="admin_stats_new_week")],
        [InlineKeyboardButton("📋 Активные пользователи за неделю", callback_data="admin_stats_active_week")],
        [InlineKeyboardButton("📋 Не подписались на каналы", callback_data="admin_stats_not_subscribed")],
        [InlineKeyboardButton(BUTTON_BACK, callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    
    # Логирование статистики
    await log_statistics({
        "new_users": {"day": new_users_day, "week": new_users_week, "month": new_users_month},
        "active_users": {"day": active_day, "week": active_week, "month": active_month},
        "publications": {"day": pub_day, "week": pub_week, "month": pub_month, "total": total_publications},
        "publications_by_chat": publications_by_chat
    })


async def admin_toggle_subscription_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключение флага проверки подписки"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    current_value = await get_subscription_check_flag()
    new_value = not current_value
    await set_subscription_check_flag(new_value)
    
    await log_action("SUBSCRIPTION_CHECK_TOGGLED", update.effective_user.id, 
                          update.effective_user.username, f"New value: {new_value}")
    
    await show_admin_panel(update, context)


async def admin_add_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление района"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        return
    
    await query.edit_message_text("Введите название нового района:")
    if update.effective_user.id not in user_data:
        user_data[update.effective_user.id] = {}
    user_data[update.effective_user.id]["admin_action"] = "add_district"
    return ADMIN_EDITING_DISTRICT


async def admin_delete_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление района"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        return
    
    districts_config = await get_districts_config()
    if not districts_config:
        await query.edit_message_text("Нет районов для удаления.")
        return
    
    districts_config = await get_districts_config()
    keyboard = [[InlineKeyboardButton(district, callback_data=f"delete_district_{district}")] 
                for district in districts_config.keys()]
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="admin_districts_config")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("Выберите район для удаления:", reply_markup=reply_markup)


async def delete_district_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка удаления района"""
    query = update.callback_query
    await query.answer()
    
    district = query.data.replace("delete_district_", "")
    districts_config = await get_districts_config()
    
    if district in districts_config:
        del districts_config[district]
        # Удаление из родительских связей
        for d, parents in list(districts_config.items()):
            if district in parents:
                parents.remove(district)
        await save_districts_config(districts_config)
        await log_action("DISTRICT_DELETED", update.effective_user.id, 
                              update.effective_user.username, f"District: {district}")
        await query.edit_message_text(f"Район '{district}' удален.")
    else:
        await query.edit_message_text("Район не найден.")
    
    await admin_districts_config(update, context)


async def admin_set_parent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Назначение родительского района"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        return
    
    districts_config = await get_districts_config()
    if not districts_config:
        await query.edit_message_text("Нет районов.")
        return
    
    districts_config = await get_districts_config()
    keyboard = [[InlineKeyboardButton(district, callback_data=f"set_parent_{district}")] 
                for district in districts_config.keys()]
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="admin_districts_config")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("Выберите район, для которого назначить родителя:", reply_markup=reply_markup)


async def set_parent_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор района для назначения родителя"""
    query = update.callback_query
    await query.answer()
    
    district = query.data.replace("set_parent_", "")
    districts_config = await get_districts_config()
    
    # Исключаем текущий район из списка возможных родителей
    districts_config = await get_districts_config()
    available_parents = [d for d in districts_config.keys() if d != district]
    
    if not available_parents:
        await query.edit_message_text("Нет доступных родительских районов.")
        return
    
    keyboard = [[InlineKeyboardButton(parent, callback_data=f"parent_selected_{district}_{parent}")] 
                for parent in available_parents]
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="admin_districts_config")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(f"Выберите родительский район для '{district}':", reply_markup=reply_markup)


async def parent_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора родительского района"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.replace("parent_selected_", "")
    # Формат: district_parent, но parent может содержать подчеркивания
    # Используем первый подчеркивание как разделитель
    if "_" not in data:
        await query.edit_message_text("Ошибка.")
        return
    
    parts = data.split("_", 1)
    district = parts[0]
    parent = parts[1]
    
    districts_config = await get_districts_config()
    
    if district not in districts_config:
        districts_config[district] = []
    
    if parent not in districts_config[district]:
        districts_config[district].append(parent)
        await save_districts_config(districts_config)
        await log_action("DISTRICT_PARENT_SET", update.effective_user.id, 
                              update.effective_user.username, f"District: {district}, Parent: {parent}")
        await query.edit_message_text(f"Родительский район '{parent}' назначен для '{district}'.")
    else:
        await query.edit_message_text("Этот родительский район уже назначен.")
    
    await admin_districts_config(update, context)


async def admin_add_price_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление ценового диапазона"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        return
    
    await query.edit_message_text("Введите новый диапазон в формате: название|мин|макс (например: 10000-15000|10000|15000)")
    if update.effective_user.id not in user_data:
        user_data[update.effective_user.id] = {}
    user_data[update.effective_user.id]["admin_action"] = "add_price_range"
    return ADMIN_EDITING_PRICE_RANGE


async def admin_delete_price_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление ценового диапазона"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        return
    
    price_ranges = await get_price_ranges()
    if not price_ranges:
        await query.edit_message_text("Нет диапазонов для удаления.")
        return
    
    keyboard = [[InlineKeyboardButton(range_name, callback_data=f"delete_price_range_{range_name}")] 
                for range_name in price_ranges.keys()]
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="admin_price_config")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("Выберите диапазон для удаления:", reply_markup=reply_markup)


async def delete_price_range_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка удаления ценового диапазона"""
    query = update.callback_query
    await query.answer()
    
    range_name = query.data.replace("delete_price_range_", "")
    price_ranges = await get_price_ranges()
    
    if range_name in price_ranges:
        del price_ranges[range_name]
        await save_price_ranges(price_ranges)
        await log_action("PRICE_RANGE_DELETED", update.effective_user.id, 
                              update.effective_user.username, f"Range: {range_name}")
        await query.edit_message_text(f"Диапазон '{range_name}' удален.")
    else:
        await query.edit_message_text("Диапазон не найден.")
    
    await admin_price_config(update, context)


async def admin_add_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление типа комнат"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        return
    
    await query.edit_message_text("Введите название нового типа комнат:")
    if update.effective_user.id not in user_data:
        user_data[update.effective_user.id] = {}
    user_data[update.effective_user.id]["admin_action"] = "add_room"
    return ADMIN_EDITING_DISTRICT  # Используем то же состояние


async def admin_delete_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление типа комнат"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        return
    
    rooms = await get_rooms_config()
    if not rooms:
        await query.edit_message_text("Нет типов для удаления.")
        return
    
    keyboard = [[InlineKeyboardButton(room, callback_data=f"delete_room_{room}")] 
                for room in rooms]
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="admin_rooms_config")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("Выберите тип для удаления:", reply_markup=reply_markup)


async def delete_room_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка удаления типа комнат"""
    query = update.callback_query
    await query.answer()
    
    room = query.data.replace("delete_room_", "")
    rooms = await get_rooms_config()
    
    if room in rooms:
        rooms.remove(room)
        await save_rooms_config(rooms)
        await log_action("ROOM_DELETED", update.effective_user.id, 
                              update.effective_user.username, f"Room: {room}")
        await query.edit_message_text(f"Тип '{room}' удален.")
    else:
        await query.edit_message_text("Тип не найден.")
    
    await admin_rooms_config(update, context)


async def admin_editing_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода при редактировании конфигураций"""
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        return ConversationHandler.END
    
    action = user_data.get(user.id, {}).get("admin_action")
    text = update.message.text.strip()
    
    if action == "add_district":
        districts_config = await get_districts_config()
        if text not in districts_config:
            districts_config[text] = []
            await save_districts_config(districts_config)
            await log_action("DISTRICT_ADDED", user.id, user.username, f"District: {text}")
            await update.message.reply_text(f"Район '{text}' добавлен.")
        else:
            await update.message.reply_text("Такой район уже существует.")
        await admin_districts_config(update, context)
        if user.id in user_data:
            del user_data[user.id]["admin_action"]
        return ConversationHandler.END
        
    elif action == "add_price_range":
        try:
            parts = text.split('|')
            if len(parts) == 3:
                range_name = parts[0].strip()
                min_price = float(parts[1].strip())
                max_price = float(parts[2].strip())
                
                price_ranges = await get_price_ranges()
                price_ranges[range_name] = [min_price, max_price]
                await save_price_ranges(price_ranges)
                await log_action("PRICE_RANGE_ADDED", user.id, user.username, f"Range: {range_name}")
                await update.message.reply_text(f"Диапазон '{range_name}' добавлен.")
            else:
                await update.message.reply_text("Неверный формат. Используйте: название|мин|макс")
                return ADMIN_EDITING_PRICE_RANGE
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {str(e)}")
            return ADMIN_EDITING_PRICE_RANGE
        await admin_price_config(update, context)
        if user.id in user_data:
            del user_data[user.id]["admin_action"]
        return ConversationHandler.END
        
    elif action == "add_room":
        rooms = await get_rooms_config()
        if text not in rooms:
            rooms.append(text)
            await save_rooms_config(rooms)
            await log_action("ROOM_ADDED", user.id, user.username, f"Room: {text}")
            await update.message.reply_text(f"Тип '{text}' добавлен.")
        else:
            await update.message.reply_text("Такой тип уже существует.")
        await admin_rooms_config(update, context)
        if user.id in user_data:
            del user_data[user.id]["admin_action"]
        return ConversationHandler.END
        
    elif action == "change_hashtag_suffix":
        if not text.startswith("_"):
            await update.message.reply_text("Суффикс должен начинаться с подчеркивания (например: _ф, _кк, _ключи)")
            return ADMIN_EDITING_HASHTAG_SUFFIX
        
        await save_hashtag_suffix(text)
        await log_action("HASHTAG_SUFFIX_CHANGED", user.id, user.username, f"New suffix: {text}")
        await update.message.reply_text(f"Суффикс хэштегов изменен на '{text}'.\n\nВсе новые публикации будут использовать новый суффикс.")
        await admin_hashtags(update, context)
        if user.id in user_data:
            del user_data[user.id]["admin_action"]
        return ConversationHandler.END
        
    elif action == "add_role":
        roles = await get_roles_config()
        if text not in roles:
            roles.append(text)
            await save_roles_config(roles)
            await log_action("ROLE_ADDED", user.id, user.username, f"Role: {text}")
            await update.message.reply_text(f"Роль '{text}' добавлена.")
        else:
            await update.message.reply_text("Такая роль уже существует.")
        await admin_manage_roles(update, context)
        if user.id in user_data:
            del user_data[user.id]["admin_action"]
        return ConversationHandler.END
    
    return ConversationHandler.END


async def delete_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /Delete_Chat_{chat_id} для удаления чата"""
    # Проверка, что сообщение из личного чата
    if not await is_private_chat(update):
        return
    
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        await update.message.reply_text(ERROR_ACCESS_DENIED)
        return
    
    command_text = update.message.text.strip()
    await log_action("DELETE_CHAT_COMMAND_RECEIVED", user.id, user.username, f"Command: {command_text}")
    
    # Извлекаем chat_id из команды /Delete_Chat_{chat_id}
    if command_text.startswith("/Delete_Chat_"):
        chat_id = command_text.replace("/Delete_Chat_", "").strip()
    else:
        await update.message.reply_text("Используйте команду в формате: /Delete_Chat_{chat_id}")
        return
    
    # Проверяем существование чата
    chats = await get_chats()
    if chat_id not in chats:
        await update.message.reply_text(f"Чат с ID {chat_id} не найден.")
        return
    
    chat_data = chats[chat_id]
    chat_title = chat_data.get('title', 'Без названия')
    
    # Запрашиваем подтверждение
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_chat_{chat_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_delete_chat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    chat_type = chat_data.get('type', 'неизвестно')
    chat_params = chat_data.get('params', '')
    
    # Форматирование типа и параметров
    type_text = ""
    if chat_type == "price_range":
        if isinstance(chat_params, list) and len(chat_params) == 2:
            type_text = f"Диапазон: {chat_params[0]}-{chat_params[1]} тыс. руб."
        else:
            type_text = f"Тип: {chat_type}"
    elif chat_type == "rooms":
        type_text = f"Тип комнат: {chat_params}"
    elif chat_type == "district":
        type_text = f"Район: {chat_params}"
    else:
        type_text = f"Тип: {chat_type}"
    
    await update.message.reply_text(
        f"Вы уверены, что хотите удалить чат?\n\n"
        f"<b>Название:</b> {chat_title}\n"
        f"<b>ID:</b> <code>{chat_id}</code>\n"
        f"<b>Тип:</b> {type_text}\n"
        f"<b>Публикаций:</b> {chat_data.get('total_publications', 0)}\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def confirm_delete_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления чата"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    chat_id = query.data.replace("confirm_delete_chat_", "")
    
    success = await delete_chat(chat_id)
    if success:
        await log_action("CHAT_DELETED", update.effective_user.id, 
                        update.effective_user.username, f"Chat ID: {chat_id}")
        await query.edit_message_text(f"✅ Чат успешно удален!")
        await admin_chat_list(update, context)
    else:
        await query.edit_message_text("Ошибка: чат не найден.")


async def cancel_delete_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена удаления чата"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Удаление отменено.")
    await admin_chat_list(update, context)


async def admin_stats_new_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список новых пользователей за неделю"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    async with aiofiles.open("users.json", 'r', encoding='utf-8') as f:
        users_content = await f.read()
        users = json.loads(users_content) if users_content.strip() else {}
    
    now = get_moscow_time()
    week_ago = format_moscow_datetime(now - timedelta(days=7), "%Y-%m-%d")
    
    new_users = []
    for user_id, user_data in users.items():
        first_seen = user_data.get("first_seen", "")
        if first_seen >= week_ago:
            username = user_data.get("username", "N/A")
            new_users.append(f"@{username}" if username != "N/A" else f"ID: {user_id}")
    
    text = "<b>Новые пользователи за неделю</b>\n\n"
    if new_users:
        text += "\n".join([f"• {user}" for user in new_users[:50]])  # Ограничение до 50
        if len(new_users) > 50:
            text += f"\n\n... и еще {len(new_users) - 50} пользователей"
    else:
        text += "Нет новых пользователей за неделю."
    
    keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="admin_statistics")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def admin_stats_active_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список активных пользователей за неделю (кто публиковал минимум 1 раз)"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    async with aiofiles.open("users.json", 'r', encoding='utf-8') as f:
        users_content = await f.read()
        users = json.loads(users_content) if users_content.strip() else {}
    async with aiofiles.open("objects.json", 'r', encoding='utf-8') as f:
        objects_content = await f.read()
        objects = json.loads(objects_content) if objects_content.strip() else {}
    
    now = get_moscow_time()
    week_ago = format_moscow_datetime(now - timedelta(days=7), "%Y-%m-%d")
    
    # Находим пользователей, которые публиковали за неделю
    active_user_ids = set()
    for obj in objects.values():
        if obj.get("status") == "опубликовано":
            pub_date = obj.get("publication_date", "")
            if pub_date >= week_ago:
                active_user_ids.add(obj.get("user_id"))
    
    active_users = []
    for user_id in active_user_ids:
        if user_id in users:
            user_data = users[user_id]
            username = user_data.get("username", "N/A")
            active_users.append(f"@{username}" if username != "N/A" else f"ID: {user_id}")
    
    text = "<b>Активные пользователи за неделю</b>\n\n"
    text += "(кто опубликовал минимум 1 объект)\n\n"
    if active_users:
        text += "\n".join([f"• {user}" for user in active_users[:50]])  # Ограничение до 50
        if len(active_users) > 50:
            text += f"\n\n... и еще {len(active_users) - 50} пользователей"
    else:
        text += "Нет активных пользователей за неделю."
    
    keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="admin_statistics")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def admin_manage_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление ролями пользователей"""
    query = update.callback_query
    
    if query:
        await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        if query:
            await query.edit_message_text(ERROR_ACCESS_DENIED)
        else:
            await update.message.reply_text(ERROR_ACCESS_DENIED)
        return
    
    users = await load_json("users.json")
    roles = await get_roles_config()
    
    # Группируем пользователей по ролям
    users_by_role = {}
    for user_id, user_data in users.items():
        role = user_data.get("role", ROLE_START)
        if role not in users_by_role:
            users_by_role[role] = []
        username = user_data.get("username", "N/A")
        users_by_role[role].append({
            "user_id": user_id,
            "username": username
        })
    
    text = "<b>Управление ролями пользователей</b>\n\n"
    text += f"<b>Роли:</b>\n"
    for role in roles:
        count = len(users_by_role.get(role, []))
        text += f"• {role}: {count}\n"
    text += "\nВыберите роль для просмотра пользователей или добавьте новую:"
    
    keyboard = []
    # Кнопки для каждой роли
    for role in roles:
        keyboard.append([InlineKeyboardButton(role, callback_data=f"admin_role_list_{role}")])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить роль", callback_data="admin_add_role")])
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="admin_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def admin_role_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список пользователей с определенной ролью"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    role = query.data.replace("admin_role_list_", "")
    users = await load_json("users.json")
    
    users_with_role = []
    for user_id, user_data in users.items():
        if user_data.get("role", ROLE_START) == role:
            username = user_data.get("username", "N/A")
            users_with_role.append({
                "user_id": user_id,
                "username": username
            })
    
    if not users_with_role:
        keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="admin_manage_roles")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Нет пользователей с ролью '{role}'.", reply_markup=reply_markup)
        return
    
    text = f"<b>Пользователи с ролью '{role}'</b>\n\n"
    
    keyboard = []
    for user in users_with_role[:50]:  # Ограничение до 50
        username_display = f"@{user['username']}" if user['username'] != "N/A" else f"ID: {user['user_id']}"
        keyboard.append([InlineKeyboardButton(username_display, callback_data=f"admin_change_role_{user['user_id']}")])
    
    if len(users_with_role) > 50:
        text += f"Показано 50 из {len(users_with_role)} пользователей\n\n"
    
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="admin_manage_roles")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def admin_change_role_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню изменения роли пользователя"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    user_id = query.data.replace("admin_change_role_", "")
    user = await get_user(user_id)
    
    if not user:
        await query.edit_message_text("Пользователь не найден.")
        return
    
    current_role = user.get("role", ROLE_START)
    username = user.get("username", "N/A")
    roles = await get_roles_config()
    
    text = f"<b>Изменение роли пользователя</b>\n\n"
    text += f"<b>Пользователь:</b> @{username if username != 'N/A' else user_id}\n"
    text += f"<b>Текущая роль:</b> {current_role}\n\n"
    text += "Выберите новую роль:"
    
    keyboard = []
    for role in roles:
        keyboard.append([InlineKeyboardButton(role, callback_data=f"admin_set_role_{user_id}_{role}")])
    
    keyboard.append([InlineKeyboardButton(BUTTON_BACK, callback_data="admin_manage_roles")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def admin_set_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка роли пользователя"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    parts = query.data.replace("admin_set_role_", "").split("_")
    user_id = parts[0]
    new_role = parts[1]
    
    await set_user_role(user_id, new_role)
    
    user = await get_user(user_id)
    username = user.get("username", "N/A") if user else "N/A"
    
    keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="admin_manage_roles")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ Роль пользователя @{username if username != 'N/A' else user_id} изменена на '{new_role}'.",
        reply_markup=reply_markup
    )


async def admin_add_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление новой роли"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        return
    
    await query.edit_message_text("Введите название новой роли:")
    if update.effective_user.id not in user_data:
        user_data[update.effective_user.id] = {}
    user_data[update.effective_user.id]["admin_action"] = "add_role"
    return ADMIN_EDITING_ROLE


async def admin_stats_not_subscribed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список пользователей, которые запустили бота, но не подписались"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text(ERROR_ACCESS_DENIED)
        return
    
    async with aiofiles.open("users.json", 'r', encoding='utf-8') as f:
        users_content = await f.read()
        users = json.loads(users_content) if users_content.strip() else {}
    
    not_subscribed = []
    for user_id, user_data in users.items():
        subscription_checked = user_data.get("subscription_checked", False)
        # Если пользователь запустил бота, но не прошел проверку подписки
        if not subscription_checked:
            username = user_data.get("username", "N/A")
            not_subscribed.append(f"@{username}" if username != "N/A" else f"ID: {user_id}")
    
    text = "<b>Пользователи, не подписавшиеся на каналы</b>\n\n"
    text += "(запустили бота, но не прошли проверку подписки)\n\n"
    if not_subscribed:
        text += "\n".join([f"• {user}" for user in not_subscribed[:50]])  # Ограничение до 50
        if len(not_subscribed) > 50:
            text += f"\n\n... и еще {len(not_subscribed) - 50} пользователей"
    else:
        text += "Все пользователи подписаны на каналы."
    
    keyboard = [[InlineKeyboardButton(BUTTON_BACK, callback_data="admin_statistics")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в админ-панель"""
    query = update.callback_query
    await query.answer()
    
    # Очистка временных данных админа при возврате
    user = update.effective_user
    if user.id in user_data:
        # Очищаем только админские данные, сохраняя данные объектов
        admin_keys = ["admin_chat_id", "admin_chat_title", "admin_chat_type", "admin_action"]
        for key in admin_keys:
            if key in user_data[user.id]:
                del user_data[user.id][key]
    
    await show_admin_panel(update, context)


async def edit_object_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /edit_id для редактирования объекта"""
    logger.info(f"edit_object_command called - Update type: {type(update)}, Has message: {update.message is not None}")
    # Проверка, что сообщение из личного чата
    if not await is_private_chat(update):
        logger.warning("edit_object_command - Not a private chat, returning ConversationHandler.END")
        return ConversationHandler.END
    
    user = update.effective_user
    command_text = update.message.text.strip()
    
    logger.info(f"EDIT_COMMAND_RECEIVED_DETAILS - User: {user.id}, Command: {command_text}")
    await log_action("EDIT_COMMAND_RECEIVED", user.id, user.username, f"Command: {command_text}")
    
    # Очищаем предыдущее состояние ConversationHandler перед началом редактирования
    conv_state = context.user_data.get('_conversation_state', 'N/A')
    logger.info(f"EDIT_COMMAND - Clearing previous conversation state: {conv_state}")
    context.user_data.pop('_conversation_state', None)
    context.user_data.pop('_conversation_name', None)
    conv_keys = [k for k in list(context.user_data.keys()) if k.startswith('_conversation')]
    for key in conv_keys:
        context.user_data.pop(key, None)
    
    # Извлекаем object_id из команды /edit_obj_xxxxxx или /edit_xxxxxx
    if command_text.startswith("/edit_"):
        object_id = command_text.replace("/edit_", "").strip()
        # Если формат /edit_obj_xxxxxx, оставляем как есть
        if object_id.startswith("obj_"):
            object_id = object_id
        else:
            # Если просто /edit_xxxxxx, добавляем префикс obj_
            object_id = f"obj_{object_id}"
    else:
        logger.warning(f"EDIT_COMMAND_INVALID_FORMAT - User: {user.id}, Command: {command_text}")
        await log_action("EDIT_COMMAND_INVALID_FORMAT", user.id, user.username, f"Command: {command_text}")
        await update.message.reply_text("Используйте команду в формате: /edit_obj_xxxxxx")
        return ConversationHandler.END
    
    logger.info(f"EDIT_COMMAND_PARSED - User: {user.id}, Object ID: {object_id}")
    
    # Проверяем, что объект существует и принадлежит пользователю
    obj = await get_object(object_id)
    if not obj:
        logger.error(f"EDIT_COMMAND_OBJECT_NOT_FOUND - User: {user.id}, Object ID: {object_id}")
        await log_action("EDIT_COMMAND_OBJECT_NOT_FOUND", user.id, user.username, f"Object ID: {object_id}")
        await update.message.reply_text("Объект не найден.")
        return ConversationHandler.END
    
    if obj.get("user_id") != str(user.id):
        logger.warning(f"EDIT_COMMAND_ACCESS_DENIED - User: {user.id}, Object ID: {object_id}, Owner: {obj.get('user_id')}")
        await log_action("EDIT_COMMAND_ACCESS_DENIED", user.id, user.username, f"Object ID: {object_id}, Owner: {obj.get('user_id')}")
        await update.message.reply_text("Этот объект вам не принадлежит.")
        return ConversationHandler.END
    
    # Инициализация временных данных для редактирования
    user_data[user.id] = {
        "object_id": object_id,
        "districts": obj.get("districts", [])
    }
    
    logger.info(f"OBJECT_EDIT_STARTED - User: {user.id}, Object: {object_id}, Districts: {user_data[user.id]['districts']}")
    await log_action("OBJECT_EDIT_STARTED", user.id, user.username, f"Object: {object_id}")
    
    # Показываем предпросмотр с меню расширенных настроек
    user_info = await get_user(str(user.id))
    await show_object_preview_with_menu(update, context, obj, user_info)
    
    # Логируем возвращаемое состояние и состояние ConversationHandler
    logger.info(f"OBJECT_EDIT_RETURNING_STATE - Object: {object_id}, State: {OBJECT_PREVIEW_MENU}, Context state before: {context.user_data.get('_conversation_state', 'N/A')}")
    await log_action("OBJECT_EDIT_RETURNING_STATE", user.id, user.username, f"Object: {object_id}, State: {OBJECT_PREVIEW_MENU}, Context state: {context.user_data.get('_conversation_state', 'N/A')}")
    
    # Возвращаем состояние - ConversationHandler должен установить его автоматически
    state = OBJECT_PREVIEW_MENU
    logger.info(f"OBJECT_EDIT_SETTING_STATE - Object: {object_id}, Returning state: {state}")
    await log_action("OBJECT_EDIT_SETTING_STATE", user.id, user.username, f"Object: {object_id}, Setting state: {state}")
    
    # Явно фиксируем состояние диалога, чтобы ConversationHandler не терял его
    context.user_data["_conversation_state"] = state
    context.user_data["_conversation_name"] = "add_object_handler"

    return state


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await log_action("BACK_TO_MENU_CLICKED", user.id, user.username)
    
    # ИСПРАВЛЕНО: Очищаем состояние ConversationHandler
    conv_state = context.user_data.get('_conversation_state', 'N/A')
    logger.info(f"BACK_TO_MENU - User: {user.id}, Current conv state: {conv_state}")
    
    # Если мы в процессе создания объекта (любой этап викторины), удаляем созданный объект
    if conv_state in [OBJECT_WAITING_ROOMS, OBJECT_WAITING_DISTRICT, OBJECT_WAITING_PRICE, 
                      OBJECT_WAITING_AREA, OBJECT_WAITING_FLOOR, OBJECT_WAITING_COMMENT, 
                      OBJECT_WAITING_EDIT_ROOMS]:
        if user.id in user_data and "object_id" in user_data[user.id]:
            object_id = user_data[user.id]["object_id"]
            await delete_object(object_id)
            await log_action("OBJECT_DELETED_ON_EXIT", user.id, user.username, f"Object: {object_id}")
            logger.info(f"BACK_TO_MENU - Deleted object {object_id} created during object creation")
    
    # Очищаем состояние ConversationHandler - полностью удаляем все связанные ключи
    context.user_data.pop('_conversation_state', None)
    context.user_data.pop('_conversation_name', None)
    # Очищаем все ключи, связанные с ConversationHandler
    conv_keys = [k for k in list(context.user_data.keys()) if k.startswith('_conversation')]
    for key in conv_keys:
        context.user_data.pop(key, None)
    logger.info(f"BACK_TO_MENU - Cleared conversation keys: {conv_keys}")
    
    # Очистка временных данных при возврате в меню
    if user.id in user_data:
        logger.info(f"BACK_TO_MENU - Clearing user_data for user {user.id}")
        del user_data[user.id]
    
    await show_main_menu(update, context)
    
    # Возвращаем ConversationHandler.END, чтобы завершить текущий диалог
    return ConversationHandler.END


# ==================== Главная функция ====================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок с расширенным логированием"""
    try:
        user = None
        username = None
        callback_data = None
        
        if isinstance(update, Update):
            if update.effective_user:
                user = update.effective_user.id
                username = update.effective_user.username
            if update.callback_query:
                callback_data = update.callback_query.data
        
        error_msg = str(context.error)
        logger.error(f"ERROR_OCCURRED - User: {user}, Username: {username}, Callback: {callback_data}, Update: {type(update)}, Error: {error_msg}", exc_info=context.error)
        await log_action("ERROR_OCCURRED", user, username, 
                        f"Error: {error_msg}, Callback: {callback_data}, Update: {type(update)}")
        
        print(f"\n{'#'*80}")
        print(f"ERROR: {error_msg}")
        print(f"Update type: {type(update)}")
        if callback_data:
            print(f"Callback data: {callback_data}")
        print(f"{'#'*80}\n")
        import traceback
        traceback.print_exc()
    except Exception as e:
        logger.error(f"Error in error_handler: {e}", exc_info=True)

def main():
    """Главная функция запуска бота"""
    # Запуск фоновой задачи для запланированных публикаций
    async def start_background_tasks(app: Application):
        """Запуск фоновых задач"""
        asyncio.create_task(process_scheduled_publications(app))
        asyncio.create_task(process_autopublish_queues(app))
    
    # Создание приложения с post_init
    application = Application.builder().token(API_TOKEN).post_init(start_background_tasks).build()
    
    # Добавление обработчика ошибок
    application.add_error_handler(error_handler)
    
    # Глобальный обработчик для логирования всех callback_query (должен быть первым)
    async def callback_query_logger(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обертка для логирования всех callback_query"""
        await log_callback_query(update, context)
        
        # Логируем состояние ConversationHandler
        if update.callback_query:
            user_id = update.effective_user.id if update.effective_user else None
            if user_id:
                # Проверяем состояние в context.user_data (это где ConversationHandler хранит состояние)
                conv_state = context.user_data.get('_conversation_state', 'N/A')
                conv_name = context.user_data.get('_conversation_name', 'N/A')
                
                # Проверяем все ключи, связанные с ConversationHandler
                conv_keys = [k for k in context.user_data.keys() if k.startswith('_conversation')]
                
                await log_action("CALLBACK_QUERY_CONV_STATE", user_id, 
                               update.effective_user.username if update.effective_user else None,
                               f"Callback: {update.callback_query.data}, Conv state: {conv_state}, Conv name: {conv_name}, Conv keys: {conv_keys}, All context keys: {list(context.user_data.keys())}")
                
                # Дополнительная проверка - может быть состояние хранится по-другому
                if conv_state == 'N/A':
                    # Проверяем, может быть состояние хранится в другом формате
                    for key, value in context.user_data.items():
                        if isinstance(value, (int, str)) and (str(value) == '3' or value == 3):
                            await log_action("CALLBACK_QUERY_POSSIBLE_STATE", user_id, 
                                           update.effective_user.username if update.effective_user else None,
                                           f"Found possible state: {key} = {value}")
    
    # Глобальный обработчик для логирования всех текстовых сообщений
    async def message_text_logger(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обертка для логирования всех текстовых сообщений"""
        if update.message and update.message.text:
            user_id = update.effective_user.id if update.effective_user else None
            if user_id:
                conv_state = context.user_data.get('_conversation_state', 'N/A')
                conv_name = context.user_data.get('_conversation_name', 'N/A')
                conv_keys = [k for k in context.user_data.keys() if k.startswith('_conversation')]
                
                logger.info(f"MESSAGE_TEXT_RECEIVED | User: {user_id} | Text: {update.message.text[:50]}... | "
                           f"Conv state: {conv_state} | Conv name: {conv_name} | Conv keys: {conv_keys}")
                await log_action("MESSAGE_TEXT_RECEIVED", user_id, 
                               update.effective_user.username if update.effective_user else None,
                               f"Text: {update.message.text[:100]}..., Conv state: {conv_state}, Conv name: {conv_name}")
    
    # Регистрируем обработчики для логирования (с низким приоритетом, чтобы не перехватывать)
    application.add_handler(CallbackQueryHandler(callback_query_logger, pattern=".*"), group=-1)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_text_logger), group=-1)
    
    # Глобальный обработчик для логирования всех команд
    async def command_logger(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обертка для логирования всех команд"""
        if update.message and update.message.text and update.message.text.startswith("/"):
            user_id = update.effective_user.id if update.effective_user else None
            if user_id:
                command = update.message.text.split()[0] if update.message.text.split() else ""
                logger.info(f"COMMAND_RECEIVED | User: {user_id} | Command: {command} | Full text: {update.message.text}")
                await log_action("COMMAND_RECEIVED", user_id, 
                               update.effective_user.username if update.effective_user else None,
                               f"Command: {command}, Full text: {update.message.text}")
    
    # Регистрируем обработчик для логирования команд (с низким приоритетом)
    application.add_handler(MessageHandler(filters.COMMAND, command_logger), group=-1)
    
    # Обработчик команды /start
    application.add_handler(CommandHandler("start", start_command))
    
    # Регистрируем обработчик для команд вида /delete_obj_*
    application.add_handler(MessageHandler(filters.Regex("^/delete_obj_.*") & filters.COMMAND, delete_object_command))
    application.add_handler(MessageHandler(filters.Regex("^/delete_obj_.*") & ~filters.COMMAND, delete_object_command))
    
    # ИСПРАВЛЕНО: Убрали standalone handler для /edit_obj_*, так как он дублировал обработку
    # Команда теперь обрабатывается только через entry point в ConversationHandler
    
    # Обработчик проверки подписки
    application.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
    
    # Регистрируем обработчик add_object отдельно с высоким приоритетом
    # Это нужно, чтобы он всегда срабатывал, даже если ConversationHandler не активен
    async def add_object_standalone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отдельный обработчик кнопки add_object с высоким приоритетом"""
        if update.callback_query and update.callback_query.data == "add_object":
            logger.info(f"add_object_standalone_handler called")
            user = update.effective_user
            
            # ИСПРАВЛЕНО: Полностью очищаем состояние ConversationHandler перед обработкой
            conv_state = context.user_data.get('_conversation_state', 'N/A')
            logger.info(f"add_object_standalone_handler - User: {user.id}, Current conv state: {conv_state}")
            
            # Очищаем все ключи, связанные с ConversationHandler
            context.user_data.pop('_conversation_state', None)
            context.user_data.pop('_conversation_name', None)
            conv_keys = [k for k in list(context.user_data.keys()) if k.startswith('_conversation')]
            for key in conv_keys:
                context.user_data.pop(key, None)
            logger.info(f"add_object_standalone_handler - Cleared conversation keys: {conv_keys}")
            
            # Очищаем временные данные пользователя, если они есть
            if user.id in user_data:
                old_object_id = user_data[user.id].get("object_id", "N/A")
                logger.info(f"add_object_standalone_handler - Clearing old user_data, old object_id: {old_object_id}")
                # Если есть незавершенный объект, удаляем его
                if "object_id" in user_data[user.id]:
                    try:
                        await delete_object(user_data[user.id]["object_id"])
                        logger.info(f"add_object_standalone_handler - Deleted old object: {old_object_id}")
                    except Exception as e:
                        logger.error(f"add_object_standalone_handler - Error deleting old object {old_object_id}: {e}")
                user_data.pop(user.id, None)
            
            # Вызываем add_object_start, который вернет состояние для ConversationHandler
            # Важно: мы возвращаем результат, чтобы ConversationHandler мог обработать его
            result = await add_object_start(update, context)
            logger.info(f"add_object_standalone_handler returning - Result: {result}")
            # Возвращаем результат, чтобы ConversationHandler мог перейти в нужное состояние
            return result
    
    application.add_handler(CallbackQueryHandler(add_object_standalone_handler, pattern="^add_object$"), group=1)
    
    # ИСПРАВЛЕНО: Регистрируем команду /edit_* отдельно ПЕРЕД ConversationHandler
    # Это нужно, чтобы она обрабатывалась как entry point
    async def edit_object_entry_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обертка для команды /edit_* как entry point"""
        logger.info(f"edit_object_entry_wrapper called - Command: {update.message.text if update.message else 'N/A'}")
        # Очищаем состояние ConversationHandler перед обработкой (на случай если оно было активно)
        context.user_data.pop('_conversation_state', None)
        context.user_data.pop('_conversation_name', None)
        conv_keys = [k for k in list(context.user_data.keys()) if k.startswith('_conversation')]
        for key in conv_keys:
            context.user_data.pop(key, None)
        result = await edit_object_command(update, context)
        logger.info(f"edit_object_entry_wrapper returning - Result: {result}")
        return result
    
    # Обработчик добавления объекта (ConversationHandler)
    # ИСПРАВЛЕНО: per_message=False, чтобы MessageHandler в entry_points работал правильно
    add_object_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_object_start, pattern="^add_object$"),
            MessageHandler(filters.Regex("^/edit_.*") & filters.COMMAND, edit_object_entry_wrapper),
            MessageHandler(filters.Regex("^/edit_.*") & ~filters.COMMAND, edit_object_entry_wrapper),
            CallbackQueryHandler(edit_object_from_autopublish, pattern="^edit_object_from_autopublish_"),
            CallbackQueryHandler(edit_object_from_list, pattern="^edit_object_from_list_")
        ],
        states={
            OBJECT_WAITING_ROOMS: [
                CallbackQueryHandler(object_rooms_selected, pattern="^rooms_"),
                CallbackQueryHandler(edit_rooms_selected, pattern="^rooms_"),
                CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$")
            ],
            OBJECT_WAITING_DISTRICT: [
                CallbackQueryHandler(object_district_selected, pattern="^district_"),
                CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$")
            ],
            OBJECT_WAITING_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, object_price_input),
                CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$")
            ],
            OBJECT_PREVIEW_MENU: [
                CallbackQueryHandler(add_more_district_menu, pattern="^add_more_district_menu$"),
                CallbackQueryHandler(add_media_menu, pattern="^add_media_menu$"),
                CallbackQueryHandler(set_comment_handler, pattern="^set_comment$"),
                CallbackQueryHandler(set_area_handler, pattern="^set_area$"),
                CallbackQueryHandler(set_floor_handler, pattern="^set_floor$"),
                CallbackQueryHandler(set_renovation_handler, pattern="^set_renovation$"),
                CallbackQueryHandler(set_address_handler, pattern="^set_address$"),
                CallbackQueryHandler(set_contacts_handler, pattern="^set_contacts$"),
                CallbackQueryHandler(edit_rooms_menu_handler, pattern="^edit_rooms_menu$"),
                CallbackQueryHandler(edit_district_menu_handler, pattern="^edit_district_menu$"),
                CallbackQueryHandler(edit_price_menu_handler, pattern="^edit_price_menu$"),
                CallbackQueryHandler(show_publication_time_menu, pattern="^publish_object$"),
                CallbackQueryHandler(publish_immediate_current, pattern="^publish_immediate_current$"),
                CallbackQueryHandler(confirm_publish_handler, pattern="^confirm_publish_"),
                CallbackQueryHandler(publish_object_immediate, pattern="^publish_immediate_"),
                CallbackQueryHandler(publish_schedule_menu_handler, pattern="^publish_schedule_menu$"),
                CallbackQueryHandler(show_date_slots, pattern="^date_"),
                CallbackQueryHandler(select_time_slot, pattern="^slot_"),
                CallbackQueryHandler(show_publication_time_menu, pattern="^back_to_publish_"),
                CallbackQueryHandler(save_draft_handler, pattern="^save_draft$"),
                CallbackQueryHandler(delete_current_object, pattern="^delete_current_object$"),
                CallbackQueryHandler(delete_current_confirm, pattern="^delete_current_confirm$"),
                CallbackQueryHandler(auto_publish_settings, pattern="^auto_publish_settings$"),
                CallbackQueryHandler(toggle_autopublish_handler, pattern="^toggle_autopublish$"),
                CallbackQueryHandler(toggle_user_autopublish_handler, pattern="^toggle_user_autopublish$"),
                CallbackQueryHandler(edit_object_from_autopublish, pattern="^edit_object_from_autopublish_"),
                CallbackQueryHandler(edit_object_from_list, pattern="^edit_object_from_list_"),
                CallbackQueryHandler(autopublish_time_handler, pattern="^autopublish_time_"),
                CallbackQueryHandler(autopublish_slot_handler, pattern="^autopublish_slot_"),
                CallbackQueryHandler(show_autopublish_slots_menu, pattern="^autopublish_time_slots$"),
                CallbackQueryHandler(cancel_object, pattern="^cancel_object$"),
                CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"),
                CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$")
            ],
            OBJECT_WAITING_ADD_DISTRICT: [
                CallbackQueryHandler(add_district_from_menu, pattern="^district_"),
                CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$")
            ],
            OBJECT_WAITING_MEDIA: [
                MessageHandler(filters.PHOTO | filters.VIDEO, media_added_from_menu),
                CommandHandler("skip", back_to_preview_handler)
            ],
            OBJECT_WAITING_AREA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, area_input),
                CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$")
            ],
            OBJECT_WAITING_FLOOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, floor_input),
                CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$")
            ],
            OBJECT_WAITING_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, comment_input),
                CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$")
            ],
            OBJECT_WAITING_RENOVATION: [
                CallbackQueryHandler(renovation_selected, pattern="^renovation_"),
                CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$")
            ],
            OBJECT_WAITING_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, address_input),
                CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$")
            ],
            OBJECT_WAITING_CONTACTS: [
                CallbackQueryHandler(phone_from_settings_menu, pattern="^phone_from_settings_menu$"),
                CallbackQueryHandler(phone_custom_menu, pattern="^phone_custom_menu$"),
                CallbackQueryHandler(set_contact_name_menu_handler, pattern="^set_contact_name_menu$"),
                CallbackQueryHandler(toggle_show_username_handler, pattern="^toggle_show_username$"),
                CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, phone_custom_input)
            ],
            OBJECT_WAITING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, contact_name_input_from_menu),
                CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$")
            ],
            OBJECT_WAITING_EDIT_ROOMS: [
                CallbackQueryHandler(edit_rooms_selected, pattern="^rooms_"),
                CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$")
            ],
            OBJECT_WAITING_EDIT_DISTRICT: [
                CallbackQueryHandler(edit_district_selected, pattern="^district_"),
                CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$")
            ],
            OBJECT_WAITING_EDIT_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_price_input),
                CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_object),
            MessageHandler(filters.Regex("^/edit_.*") & filters.COMMAND, edit_object_entry_wrapper),
            MessageHandler(filters.Regex("^/edit_.*") & ~filters.COMMAND, edit_object_entry_wrapper)
        ],
        per_message=False,  # ИСПРАВЛЕНО: False для работы с MessageHandler в entry_points и states
        per_chat=True,
        per_user=True
    )
    application.add_handler(add_object_handler)
    
    # Обработчик команды /edit_id (отдельно для удобства) - регистрируем как entry_point в ConversationHandler
    # Команда обрабатывается через entry_points в add_object_handler
    
    # Обработчики для "Мои объекты"
    application.add_handler(CallbackQueryHandler(my_objects, pattern="^my_objects$"))
    application.add_handler(CallbackQueryHandler(my_objects, pattern="^my_objects_page_"))
    application.add_handler(CallbackQueryHandler(view_object, pattern="^view_object_"))
    application.add_handler(CallbackQueryHandler(delete_object_callback, pattern="^delete_object_"))
    application.add_handler(CallbackQueryHandler(delete_object_from_list, pattern="^delete_object_from_list_"))
    application.add_handler(CallbackQueryHandler(confirm_delete_object, pattern="^confirm_delete_"))
    application.add_handler(CallbackQueryHandler(publish_draft, pattern="^publish_draft_"))
    
    # Обработчики настроек
    settings_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(settings_add_phone, pattern="^settings_add_phone$"),
            CallbackQueryHandler(settings_change_phone, pattern="^settings_change_phone$"),
            CallbackQueryHandler(settings_set_name, pattern="^settings_set_name$")
        ],
        states={
            SETTINGS_WAITING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, settings_phone_input)],
            SETTINGS_WAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, settings_name_input)]
        },
        fallbacks=[CommandHandler("cancel", back_to_menu)],
        per_message=False,
        per_chat=True,
        per_user=True
    )
    application.add_handler(settings_handler)
    application.add_handler(CallbackQueryHandler(settings, pattern="^settings$"))
    application.add_handler(CallbackQueryHandler(settings_profile_info, pattern="^settings_profile_info$"))
    application.add_handler(CallbackQueryHandler(settings_toggle_default_username, pattern="^settings_toggle_default_username$"))
    application.add_handler(CallbackQueryHandler(settings_toggle_footer, pattern="^settings_toggle_footer$"))
    
    # Обработчик настроек автопубликации (отдельно, чтобы работал всегда)
    application.add_handler(CallbackQueryHandler(auto_publish_settings, pattern="^auto_publish_settings$"))
    application.add_handler(CallbackQueryHandler(publish_schedule_menu_handler, pattern="^publish_schedule_menu$"))
    application.add_handler(CallbackQueryHandler(autopublish_time_handler, pattern="^autopublish_time_"))
    application.add_handler(CallbackQueryHandler(show_autopublish_slots_menu, pattern="^autopublish_time_slots$"))
    application.add_handler(CallbackQueryHandler(autopublish_slot_handler, pattern="^autopublish_slot_"))
    application.add_handler(CallbackQueryHandler(toggle_user_autopublish_handler, pattern="^toggle_user_autopublish$"))
    
    # Другие обработчики
    application.add_handler(CallbackQueryHandler(all_chats, pattern="^all_chats$"))
    application.add_handler(CallbackQueryHandler(contact_admin, pattern="^contact_admin$"))
    
    # Обработчики админ-панели
    admin_add_chat_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_chat_start, pattern="^admin_add_chat$")],
        states={
            ADMIN_WAITING_CHAT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_chat_id_input)],
            ADMIN_WAITING_CHAT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_chat_title_input)],
            ADMIN_WAITING_CHAT_TYPE: [CallbackQueryHandler(admin_chat_type_selected, pattern="^chat_type_")],
            ADMIN_WAITING_CHAT_PARAMS: [
                CallbackQueryHandler(admin_chat_params_selected, pattern="^chat_param_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_chat_params_input)
            ]
        },
        fallbacks=[CommandHandler("cancel", admin_back)]
    )
    application.add_handler(admin_add_chat_handler)
    application.add_handler(CallbackQueryHandler(admin_chat_list, pattern="^admin_chat_list$"))
    application.add_handler(CallbackQueryHandler(admin_districts_config, pattern="^admin_districts_config$"))
    application.add_handler(CallbackQueryHandler(admin_price_config, pattern="^admin_price_config$"))
    application.add_handler(CallbackQueryHandler(admin_rooms_config, pattern="^admin_rooms_config$"))
    application.add_handler(CallbackQueryHandler(admin_hashtags, pattern="^admin_hashtags$"))
    application.add_handler(CallbackQueryHandler(admin_change_hashtag_suffix, pattern="^admin_change_hashtag_suffix$"))
    application.add_handler(CallbackQueryHandler(admin_statistics, pattern="^admin_statistics$"))
    application.add_handler(CallbackQueryHandler(admin_stats_new_week, pattern="^admin_stats_new_week$"))
    application.add_handler(CallbackQueryHandler(admin_stats_active_week, pattern="^admin_stats_active_week$"))
    application.add_handler(CallbackQueryHandler(admin_stats_not_subscribed, pattern="^admin_stats_not_subscribed$"))
    application.add_handler(CallbackQueryHandler(admin_toggle_subscription_check, pattern="^admin_toggle_subscription_check$"))
    application.add_handler(CallbackQueryHandler(admin_manage_roles, pattern="^admin_manage_roles$"))
    application.add_handler(CallbackQueryHandler(admin_role_list, pattern="^admin_role_list_"))
    application.add_handler(CallbackQueryHandler(admin_change_role_menu, pattern="^admin_change_role_"))
    application.add_handler(CallbackQueryHandler(admin_set_role, pattern="^admin_set_role_"))
    application.add_handler(CallbackQueryHandler(admin_back, pattern="^admin_back$"))
    
    # Обработчик команды удаления чата
    application.add_handler(MessageHandler(filters.Regex("^/Delete_Chat_.*"), delete_chat_command))
    application.add_handler(CallbackQueryHandler(confirm_delete_chat, pattern="^confirm_delete_chat_"))
    application.add_handler(CallbackQueryHandler(cancel_delete_chat, pattern="^cancel_delete_chat$"))
    
    # Обработчики управления конфигурациями
    admin_config_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_add_district, pattern="^admin_add_district$"),
            CallbackQueryHandler(admin_add_price_range, pattern="^admin_add_price_range$"),
            CallbackQueryHandler(admin_add_room, pattern="^admin_add_room$"),
            CallbackQueryHandler(admin_add_role, pattern="^admin_add_role$"),
            CallbackQueryHandler(admin_change_hashtag_suffix, pattern="^admin_change_hashtag_suffix$")
        ],
        states={
            ADMIN_EDITING_DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_editing_input)],
            ADMIN_EDITING_PRICE_RANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_editing_input)],
            ADMIN_EDITING_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_editing_input)],
            ADMIN_EDITING_HASHTAG_SUFFIX: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_editing_input)]
        },
        fallbacks=[CommandHandler("cancel", admin_back)]
    )
    application.add_handler(admin_config_handler)
    
    # Обработчики удаления и управления
    application.add_handler(CallbackQueryHandler(delete_district_callback, pattern="^delete_district_"))
    application.add_handler(CallbackQueryHandler(admin_set_parent, pattern="^admin_set_parent$"))
    application.add_handler(CallbackQueryHandler(set_parent_district, pattern="^set_parent_"))
    application.add_handler(CallbackQueryHandler(parent_selected, pattern="^parent_selected_"))
    application.add_handler(CallbackQueryHandler(admin_delete_price_range, pattern="^admin_delete_price_range$"))
    application.add_handler(CallbackQueryHandler(delete_price_range_callback, pattern="^delete_price_range_"))
    application.add_handler(CallbackQueryHandler(admin_delete_room, pattern="^admin_delete_room$"))
    application.add_handler(CallbackQueryHandler(delete_room_callback, pattern="^delete_room_"))
    
    # Общие обработчики
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    application.add_handler(CommandHandler("sort_new", sort_new_command))
    application.add_handler(CommandHandler("sort_old", sort_old_command))
    application.add_handler(CommandHandler("delete_all", delete_all_objects_command))
    application.add_handler(CallbackQueryHandler(confirm_delete_all, pattern="^confirm_delete_all_"))
    
    # Запуск бота
    print("\n" + "="*80)
    print("БОТ ЗАПУЩЕН")
    print("Система планирования публикаций активирована")
    print("="*80 + "\n")
    # ИСПРАВЛЕНО: Используем правильный способ запуска бота
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()

