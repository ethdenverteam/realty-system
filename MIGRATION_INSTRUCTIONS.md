# Инструкция по выполнению миграции базы данных

## Что такое миграция?

Миграция - это способ обновить структуру базы данных (добавить новые поля, таблицы и т.д.) без потери данных.

## Как выполнить миграцию

### Вариант 1: Через командную строку (рекомендуется)

1. Откройте терминал/командную строку в корне проекта (где находится файл `alembic.ini`)

2. Выполните команду:
```bash
alembic upgrade head
```

Если у вас установлен Python через виртуальное окружение:
```bash
# Активируйте виртуальное окружение (если используется)
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Затем выполните миграцию
alembic upgrade head
```

### Вариант 2: Через Docker

Если вы используете Docker, выполните команду внутри контейнера:

```bash
docker-compose exec app alembic upgrade head
```

или

```bash
docker exec -it <container_name> alembic upgrade head
```

### Вариант 3: Через Python скрипт

Создайте файл `run_migration.py` в корне проекта:

```python
from alembic.config import Config
from alembic import command

alembic_cfg = Config("alembic.ini")
command.upgrade(alembic_cfg, "head")
```

Затем выполните:
```bash
python run_migration.py
```

## Что делает эта миграция?

Миграция `add_chat_cached_at.py` добавляет поле `cached_at` в таблицу `chats`. Это поле хранит дату и время, когда чат был закэширован из аккаунта пользователя.

## Проверка результата

После выполнения миграции вы можете проверить, что поле добавлено:

```sql
-- В PostgreSQL
\d chats
```

Или через Python:
```python
from app.database import db
from app.models.chat import Chat
from sqlalchemy import inspect

inspector = inspect(db.engine)
columns = [col['name'] for col in inspector.get_columns('chats')]
print('cached_at' in columns)  # Должно быть True
```

## Откат миграции (если нужно)

Если нужно откатить миграцию:

```bash
alembic downgrade -1
```

## Проблемы?

Если возникают ошибки:

1. Убедитесь, что база данных доступна
2. Проверьте, что все зависимости установлены (`pip install -r requirements.txt`)
3. Проверьте логи для деталей ошибки

