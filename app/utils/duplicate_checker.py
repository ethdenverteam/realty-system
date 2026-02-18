"""
Утилита для проверки дубликатов публикаций
Поддерживает 4 типа публикаций с отдельными переключателями:
- ручная бот
- ручная аккаунт
- авто бот
- авто аккаунт
+ отдельный переключатель для админа
"""
from datetime import datetime, timedelta
from app.database import db
from app.models.publication_history import PublicationHistory
from app.models.user import User


def check_duplicate_publication(
    object_id: str,
    chat_id: int,
    account_id: int = None,
    publication_type: str = 'autopublish_bot',  # manual_bot, manual_account, autopublish_bot, autopublish_account
    user_id: int = None,
    allow_duplicates_setting: dict = None
) -> tuple[bool, str]:
    """
    Проверить, можно ли публиковать объект в чат (правило "не чаще раза в сутки")
    
    Args:
        object_id: ID объекта
        chat_id: ID чата
        account_id: ID аккаунта (None для бота)
        publication_type: Тип публикации (manual_bot, manual_account, autopublish_bot, autopublish_account)
        user_id: ID пользователя (для проверки прав админа)
        allow_duplicates_setting: Настройки разрешения дубликатов из SystemSetting
            Формат: {
                'manual_bot': bool,
                'manual_account': bool,
                'autopublish_bot': bool,
                'autopublish_account': bool,
                'admin_bypass': bool  # Для админов правило не применяется
            }
    
    Returns:
        (can_publish: bool, reason: str)
    """
    # Если настройки не переданы, получаем из БД
    if allow_duplicates_setting is None:
        from app.models.system_setting import SystemSetting
        setting = SystemSetting.query.filter_by(key='allow_duplicates').first()
        if setting and isinstance(setting.value_json, dict):
            allow_duplicates_setting = setting.value_json
        else:
            # По умолчанию все правила включены (дубликаты запрещены)
            allow_duplicates_setting = {
                'manual_bot': False,
                'manual_account': False,
                'autopublish_bot': False,
                'autopublish_account': False,
                'admin_bypass': False
            }
    
    # Проверка прав админа
    if user_id and allow_duplicates_setting.get('admin_bypass', False):
        user = User.query.get(user_id)
        if user and user.web_role == 'admin':
            return True, "Админ может публиковать без ограничений"
    
    # Проверяем, разрешены ли дубликаты для этого типа публикации
    allow_duplicates = allow_duplicates_setting.get(publication_type, False)
    if allow_duplicates:
        return True, "Дубликаты разрешены для этого типа публикации"
    
    # Проверяем историю публикаций за последние 24 часа
    yesterday = datetime.utcnow() - timedelta(days=1)
    
    query = PublicationHistory.query.filter(
        PublicationHistory.object_id == object_id,
        PublicationHistory.chat_id == chat_id,
        PublicationHistory.published_at >= yesterday,
        PublicationHistory.deleted == False
    )
    
    # Для аккаунтов проверяем также account_id (один объект в один чат через один аккаунт)
    if account_id is not None:
        query = query.filter(PublicationHistory.account_id == account_id)
    else:
        # Для бота проверяем, что account_id NULL
        query = query.filter(PublicationHistory.account_id.is_(None))
    
    recent_publication = query.first()
    
    if recent_publication:
        published_at_msk = recent_publication.published_at.strftime('%Y-%m-%d %H:%M:%S UTC')
        return False, f"Объект уже был опубликован в этот чат {published_at_msk} (менее 24 часов назад)"
    
    return True, "Публикация разрешена"

