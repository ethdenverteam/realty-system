# Система управления недвижимостью

Система для управления публикацией объектов недвижимости через Telegram бота и веб-интерфейс.

## Технологический стек

- **Backend**: Flask (Python 3.11)
- **База данных**: PostgreSQL 15
- **Кэш/Очереди**: Redis 7
- **Telegram**: python-telegram-bot, Telethon
- **Фоновые задачи**: Celery
- **Веб-сервер**: Nginx
- **Контейнеризация**: Docker + Docker Compose

## Структура проекта

```
realty-system/
├── docker-compose.yml      # Docker контейнеры
├── Dockerfile              # Образ приложения
├── requirements.txt         # Python зависимости
├── alembic.ini            # Конфигурация миграций
├── .env.example           # Пример переменных окружения
├── app/                   # Flask веб-приложение
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── models/            # Модели БД (10 таблиц)
│   ├── routes/           # API роуты
│   └── utils/            # Утилиты (JWT, декораторы)
├── bot/                  # Telegram бот
│   ├── main.py
│   ├── handlers.py
│   ├── utils.py
│   └── config.py
├── workers/              # Celery воркеры
│   ├── celery_app.py
│   └── tasks.py
├── migrations/           # Миграции Alembic
├── nginx/               # Конфигурация Nginx
├── uploads/            # Загруженные файлы
├── sessions/           # Сессии Telethon
└── logs/               # Логи приложения
```

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone <repository>
cd realty-system
cp .env.example .env
# Отредактируйте .env файл с вашими настройками
```

### 2. Запуск через Docker Compose

```bash
docker-compose up -d
```

### 3. Инициализация базы данных

```bash
# Создать миграции
docker-compose exec web alembic revision --autogenerate -m "Initial migration"

# Применить миграции
docker-compose exec web alembic upgrade head
```

### 4. Доступ к сервисам

- **Веб-интерфейс**: http://localhost
- **API**: http://localhost/api
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## Модели базы данных

1. **users** - Пользователи системы
2. **objects** - Объекты недвижимости
3. **telegram_accounts** - Telegram аккаунты для публикации
4. **chats** - Чаты для публикации
5. **publication_queues** - Очереди публикаций
6. **publication_history** - История публикаций
7. **action_logs** - Логи действий
8. **statistics** - Статистика системы
9. **bot_web_codes** - Коды привязки бота к вебу
10. **system_settings** - Системные настройки

## API Endpoints

### Авторизация
- `POST /api/auth/login` - Вход по коду из бота
- `POST /api/auth/logout` - Выход
- `GET /api/auth/me` - Текущий пользователь

### Объекты
- `GET /api/objects` - Список объектов
- `POST /api/objects` - Создать объект
- `GET /api/objects/<id>` - Получить объект
- `PUT /api/objects/<id>` - Обновить объект
- `DELETE /api/objects/<id>` - Удалить объект

### Telegram аккаунты
- `GET /api/accounts` - Список аккаунтов
- `POST /api/accounts` - Добавить аккаунт
- `PUT /api/accounts/<id>` - Обновить аккаунт
- `DELETE /api/accounts/<id>` - Удалить аккаунт

### Публикации
- `POST /api/publications/queue` - Создать задачу публикации

### Админ
- `GET /api/admin/users` - Список пользователей
- `PUT /api/admin/users/<id>/role` - Изменить роль

## Telegram бот

### Команды
- `/start` - Начать работу с ботом
- `/getcode` - Получить код для входа в веб-интерфейс

## Разработка

### Локальная разработка без Docker

```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
export DATABASE_URL=postgresql://user:pass@localhost/realty_db
export REDIS_URL=redis://localhost:6379/0
export TELEGRAM_BOT_TOKEN=your_token

# Запуск Flask
flask run

# Запуск бота
python -m bot.main

# Запуск Celery worker
celery -A workers.celery_app worker --loglevel=info
```

## Миграции

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "Description"

# Применить миграции
alembic upgrade head

# Откатить миграцию
alembic downgrade -1
```

## Лицензия

MIT

