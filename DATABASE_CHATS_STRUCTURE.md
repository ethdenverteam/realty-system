# Структура базы данных чатов

## Общая информация

**Одна таблица `chats` для всех чатов** - и для бота, и для пользовательских аккаунтов.

Разделение происходит через поля:
- `owner_type` - тип владельца: `'bot'` или `'user'`
- `owner_account_id` - ID аккаунта (NULL для бота, ID для пользователя)

## Структура таблицы `chats`

```sql
CREATE TABLE chats (
    chat_id INTEGER PRIMARY KEY,
    telegram_chat_id VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL,  -- group/channel/supergroup
    category VARCHAR(100),  -- legacy категории
    filters_json JSON,  -- расширенные фильтры
    owner_type VARCHAR(10) DEFAULT 'bot' NOT NULL,  -- 'bot' или 'user'
    owner_account_id INTEGER,  -- NULL для бота, ID аккаунта для пользователя
    is_active BOOLEAN DEFAULT TRUE,
    members_count INTEGER DEFAULT 0,
    added_date TIMESTAMP,
    last_publication TIMESTAMP,
    total_publications INTEGER DEFAULT 0,
    cached_at TIMESTAMP  -- когда чат был закэширован из аккаунта
);
```

## Разделение чатов

### Чаты бота (`owner_type = 'bot'`)
- `owner_type` = `'bot'`
- `owner_account_id` = `NULL`
- Добавляются администратором через веб-интерфейс
- Используются для автоматической публикации через бота

**Пример:**
```python
Chat(
    telegram_chat_id="-1001234567890",
    title="Недвижимость Москва",
    type="supergroup",
    owner_type="bot",
    owner_account_id=None,  # NULL для бота
    filters_json={"rooms_types": ["1к", "2к"], "districts": ["Центр"]}
)
```

### Чаты пользователя (`owner_type = 'user'`)
- `owner_type` = `'user'`
- `owner_account_id` = ID из таблицы `telegram_accounts`
- Загружаются автоматически из Telegram аккаунта пользователя
- Кэшируются при загрузке через `get_account_chats`
- Используются для публикации через аккаунт пользователя

**Пример:**
```python
Chat(
    telegram_chat_id="-1009876543210",
    title="Мой канал",
    type="channel",
    owner_type="user",
    owner_account_id=5,  # ID аккаунта пользователя
    cached_at=datetime.utcnow()
)
```

## Запросы

### Получить все чаты бота:
```python
bot_chats = Chat.query.filter_by(owner_type='bot', is_active=True).all()
```

### Получить чаты конкретного аккаунта:
```python
user_chats = Chat.query.filter_by(
    owner_type='user',
    owner_account_id=account_id,
    is_active=True
).all()
```

### Получить все чаты пользователя (все его аккаунты):
```python
from app.models.telegram_account import TelegramAccount

# Получить все аккаунты пользователя
accounts = TelegramAccount.query.filter_by(owner_id=user_id).all()
account_ids = [acc.account_id for acc in accounts]

# Получить все чаты этих аккаунтов
user_chats = Chat.query.filter(
    Chat.owner_type == 'user',
    Chat.owner_account_id.in_(account_ids),
    Chat.is_active == True
).all()
```

## Важные моменты

1. **Одна таблица** - все чаты хранятся в одной таблице `chats`
2. **Разделение через поля** - `owner_type` и `owner_account_id` определяют принадлежность
3. **Уникальность** - `telegram_chat_id` должен быть уникальным (один чат = одна запись)
4. **Кэширование** - чаты пользователя кэшируются при загрузке, поле `cached_at` показывает когда
5. **Фильтры** - бот использует `filters_json` для автоматического подбора чатов, пользователь выбирает вручную

## Связи

```
users (пользователи)
  └── telegram_accounts (аккаунты пользователей)
        └── chats (чаты аккаунтов, owner_type='user')

admin (администратор)
  └── chats (чаты бота, owner_type='bot')
```

## Миграции

При добавлении новых полей (как `cached_at`) создается миграция в `migrations/versions/`.

Выполнение миграции:
```bash
alembic upgrade head
```

