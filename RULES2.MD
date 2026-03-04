# 🧠 Vibe Coding — Единое руководство для нейросети (живой документ)

> **Назначение**  
> Этот файл — **ЕДИНСТВЕННЫЙ ИСТОЧНИК ПРАВДЫ** о текущем состоянии проекта.  
> Содержит описание архитектуры, моделей, API, задач, активных проблем и бэклог.  
> **Перед каждым ответом нейросеть ОБЯЗАНА прочитать этот файл полностью.**

---

## 1. 🗂 Текущее состояние проекта

### 1.1 Стек технологий
* Frontend: React 18.2.0, TypeScript 5.3.3, Vite 5.0.8, React Router DOM 6.20.0, MobX 6.15.0, Axios 1.6.2
* Backend: Flask 3.0.0, Python 3.11, SQLAlchemy 2.0.23, Gunicorn 21.2.0, PyJWT 2.8.0, python-telegram-bot 20.7, Telethon 1.32.0, Celery 5.3.4
* БД: PostgreSQL 15, Redis 7, Alembic 1.12.1
* Инфраструктура: Docker + Compose, Nginx, Prometheus, Grafana
* Другое: python-dotenv, Pillow 10.1.0, prometheus-client, pytz 2023.3, cryptography 41.0.7

### 1.2 Текущая архитектура

**Структура проекта:**
- `app/` — Flask веб-приложение
  - `models/` — 16 моделей БД (User, Object, TelegramAccount, Chat, PublicationQueue, AccountPublicationQueue, PublicationHistory, ActionLog, Statistics, BotWebCode, SystemSetting, QuickAccess, AutopublishConfig, ChatGroup, ChatSubscriptionTask, TelegramAccountChat)
  - `routes/` — API роуты (auth, objects, accounts, chats, publications, admin_routes, user_routes, chat_subscriptions, logs, logs_viewer, dashboard, admin — legacy)
  - `utils/` — утилиты (JWT, декораторы, логирование, Telethon клиент, rate limiter, time utils, account publication utils)
  - `config.py` — конфигурация (часовой пояс МСК, время автопубликации 8:00-22:00 МСК)
  - `database.py` — инициализация БД
  - `__init__.py` — создание Flask приложения, регистрация blueprints, обработка ошибок, раздача статики React
- `bot/` — Telegram бот
  - `main.py` — точка входа, регистрация обработчиков
  - `handlers.py` — основные команды (start, getcode, main_menu)
  - `handlers_object.py` — создание объектов
  - `handlers_object_edit.py` — редактирование объектов
  - `handlers_objects_view.py` — просмотр списка объектов
  - `handlers_publication.py` — публикация объектов
  - `handlers_settings.py` — настройки пользователя
  - `utils.py` — утилиты бота (форматирование текста, конфигурация районов)
  - `utils_chat.py` — работа с чатами
  - `utils_logger.py` — логирование бота
  - `config.py` — конфигурация бота
  - `models.py` — модели БД для бота (используют app.database)
  - `database.py` — подключение к БД для бота (использует app.database)
- `workers/` — Celery воркеры
  - `celery_app.py` — конфигурация Celery, расписание задач
  - `tasks.py` — фоновые задачи (публикация, автопубликация, подписка на чаты)
- `frontend/` — React SPA
  - `src/` — исходники (components, pages, stores, contexts, hooks, utils, types)
  - `public/` — статические файлы
  - Сборка в `static/` в корне проекта
- `migrations/` — Alembic миграции
- `nginx/` — конфигурация Nginx
- `config/` — конфигурация Prometheus
- `templates/` — HTML шаблоны (legacy, используются для некоторых админ страниц)
- `static/` — собранные файлы React и загруженные файлы
- `uploads/` — загруженные файлы (фото объектов)
- `sessions/` — сессии Telethon
- `logs/` — логи приложения

**Потоки данных:**
1. Пользователь → Telegram бот → БД (app.database) → Веб‑интерфейс
2. Веб‑интерфейс → Flask API → БД (app.database) → Celery → Telegram публикация
3. Все действия логируются в БД (`action_logs`) и файлы (`logs/`)
4. Автопубликация: ежедневно в 05:00 UTC (08:00 МСК) создаются задачи в `publication_queues` и `account_publication_queues`
5. Подписка на чаты: через `chat_subscription_tasks`, обрабатывается Celery с интервалами

**Docker Compose сервисы:**
- `postgres` — PostgreSQL 15
- `redis` — Redis 7
- `web` — Flask приложение (Gunicorn, 4 воркера)
- `bot` — Telegram бот
- `celery_worker` — Celery воркер (4 потока)
- `celery_beat` — Celery beat (планировщик)
- `nginx` — веб-сервер (порт 80, 443)
- `prometheus` — мониторинг (порт 9090)
- `grafana` — дашборды (порт 3000)

### 1.3 Модели базы данных

**Основные модели (app.models):**
1. **User** — пользователи системы
   - `user_id`, `telegram_id` (unique), `username`, `phone`, `bot_role`, `web_role`, `settings_json`, `created_at`, `last_activity`, `total_publications`
   - Связи: objects, telegram_accounts, publication_queues, account_publication_queues, action_logs, bot_web_codes, quick_access_items, autopublish_configs, chat_groups

2. **Object** — объекты недвижимости
   - `object_id` (String, PK, формат ПРЕФИКС001), `user_id`, `rooms_type`, `price`, `districts_json`, `region`, `city`, `photos_json`, `area`, `floor`, `address`, `residential_complex`, `renovation`, `comment`, `contact_name`, `show_username`, `phone_number`, `contact_name_2`, `phone_number_2`, `status`, `source`, `publication_date`, `creation_date`, `updated_at`
   - Связи: user, publication_queues, account_publication_queues, publication_history, autopublish_config

3. **TelegramAccount** — Telegram аккаунты пользователей
   - `account_id`, `owner_id`, `phone` (unique), `session_file`, `mode` (aggressive/normal/safe/smart), `daily_limit`, `is_active`, `last_used`, `last_error`, `created_at`
   - Связи: owner, chats (legacy), chat_links (many-to-many через TelegramAccountChat), publication_queues, account_publication_queues

4. **Chat** — чаты для публикации
   - `chat_id`, `telegram_chat_id` (unique), `title`, `type` (group/channel/supergroup), `category` (legacy), `filters_json`, `owner_type` (bot/user), `owner_account_id` (legacy), `is_active`, `members_count`, `added_date`, `last_publication`, `total_publications`, `cached_at`
   - Связи: account (legacy), account_links (many-to-many через TelegramAccountChat)

5. **PublicationQueue** — очереди публикаций (бот)
   - `queue_id`, `object_id`, `chat_id`, `account_id`, `user_id`, `type` (bot), `mode` (immediate/scheduled/autopublish), `status` (pending/processing/completed/failed), `scheduled_time`, `created_at`, `started_at`, `completed_at`, `message_id`, `error_message`, `attempts`
   - Связи: object, chat, account, user

6. **AccountPublicationQueue** — очереди публикаций (аккаунты пользователей)
   - `queue_id`, `object_id`, `chat_id`, `account_id`, `user_id`, `status`, `scheduled_time`, `created_at`, `started_at`, `completed_at`, `message_id`, `error_message`, `attempts`
   - Связи: object, chat, account, user

7. **PublicationHistory** — история публикаций
   - `history_id`, `queue_id`, `object_id`, `chat_id`, `account_id`, `published_at`, `message_id`, `deleted`
   - Связи: object

8. **ActionLog** — логи действий пользователей
   - `log_id`, `user_id`, `action`, `details_json`, `ip_address`, `user_agent`, `created_at`
   - Связи: user

9. **Statistics** — статистика системы
   - `stat_id`, `date`, `total_users`, `total_objects`, `total_publications`, `active_users`, `details_json`

10. **BotWebCode** — коды привязки бота к вебу
    - `code_id`, `user_id`, `code`, `expires_at`, `used_at`, `created_at`
    - Связи: user

11. **SystemSetting** — системные настройки
    - `setting_id`, `key` (unique), `value_json`, `description`, `updated_at`

12. **QuickAccess** — быстрый доступ
    - `item_id`, `user_id`, `type`, `data_json`, `created_at`
    - Связи: user

13. **AutopublishConfig** — конфигурация автопубликации
    - `config_id`, `user_id`, `object_id` (unique), `enabled`, `bot_enabled`, `accounts_enabled`, `accounts_config_json`, `created_at`, `updated_at`
    - Связи: user, object

14. **ChatGroup** — группы чатов для подписки
    - `group_id`, `user_id`, `name`, `purpose`, `category`, `is_public`, `chat_links_json`, `created_at`, `updated_at`
    - Связи: user, subscription_tasks

15. **ChatSubscriptionTask** — задачи подписки на чаты
    - `task_id`, `user_id`, `account_id`, `group_id`, `status` (pending/processing/completed/failed/flood_wait), `current_index`, `total_chats`, `successful_count`, `flood_count`, `flood_wait_until`, `interval_mode` (safe/aggressive), `next_run_at`, `result`, `error_message`, `started_at`, `completed_at`, `created_at`, `estimated_completion`, `chat_links` (JSON)
    - Связи: user, account, group

16. **TelegramAccountChat** — связь many-to-many аккаунт ↔ чат
    - `link_id`, `account_id`, `chat_id`, `created_at`
    - Связи: account, chat

### 1.4 API Endpoints

**Авторизация (`/system/auth`):**
- `POST /login` — вход по коду из бота
- `POST /logout` — выход
- `GET /me` — текущий пользователь

**Объекты (`/system/objects`):**
- `GET /` — список объектов пользователя
- `POST /` — создание объекта (multipart/form-data или JSON)
- `GET /<object_id>` — получение объекта
- `PUT /<object_id>` — обновление объекта
- `DELETE /<object_id>` — удаление объекта

**Аккаунты (`/system/accounts`):**
- `GET /` — список аккаунтов пользователя
- `POST /connect/start` — начало подключения аккаунта
- `POST /connect/verify` — проверка кода подключения
- `GET /<account_id>` — получение аккаунта
- `PUT /<account_id>` — обновление аккаунта
- `DELETE /<account_id>` — удаление аккаунта

**Чаты (`/system/chats`):**
- `GET /` — список чатов пользователя
- `POST /` — добавление чата
- `GET /<chat_id>` — получение чата
- `PUT /<chat_id>` — обновление чата
- `DELETE /<chat_id>` — удаление чата

**Публикации (`/system/publications`):**
- `POST /` — создание публикации
- `GET /` — список публикаций
- `GET /<publication_id>` — получение публикации

**Админ (`/system/admin`):**
- `GET /dashboard` — дашборд админа
- `GET /stats` — статистика
- `GET /bot-chats/list` — список чатов бота
- `POST /bot-chats/fetch` — получение чатов из Telegram
- `POST /bot-chats` — добавление чата
- `PUT /bot-chats/<id>` — обновление чата
- `DELETE /bot-chats/<id>` — удаление чата
- `POST /bot-chats/<id>/test-publish` — тестовая публикация
- `GET /bot-chats/config` — конфигурация чатов
- `GET /bot-chats/districts` — список районов
- `POST /bot-chats/districts` — добавление района
- `DELETE /bot-chats/districts/<name>` — удаление района

**Пользователь (`/system/user`):**
- `GET /dashboard` — дашборд пользователя
- `GET /stats` — статистика пользователя
- `GET /settings` — настройки пользователя
- `PUT /settings` — обновление настроек

**Подписки на чаты (`/system/chat-subscriptions`):**
- `GET /groups` — список групп чатов
- `POST /groups` — создание группы
- `GET /groups/<group_id>` — получение группы
- `PUT /groups/<group_id>` — обновление группы
- `DELETE /groups/<group_id>` — удаление группы
- `POST /groups/<group_id>/subscribe` — запуск подписки
- `GET /tasks` — список задач подписки
- `GET /tasks/<task_id>` — получение задачи
- `POST /tasks/<task_id>/pause` — пауза задачи
- `POST /tasks/<task_id>/resume` — возобновление задачи

**Логи (`/api/logs`):**
- `GET /stream` — поток логов
- `GET /files` — список файлов логов
- `GET /view` — просмотр логов
- `GET /download` — скачивание логов
- `GET /file/<log_type>` — скачивание конкретного файла

### 1.5 Celery задачи

**Периодические задачи (celery beat):**
- `process-scheduled-publications-every-minute` — обработка запланированных публикаций (каждую минуту)
- `process-autopublish-every-minute` — обработка автопубликации (каждую минуту)
- `process-chat-subscriptions-every-minute` — обработка подписок на чаты (каждую минуту)
- `schedule-daily-autopublish-8-msk` — создание задач автопубликации (ежедневно в 05:00 UTC = 08:00 МСК)
- `process-account-autopublish-every-minute` — обработка очередей аккаунтов (каждую минуту)

**Асинхронные задачи:**
- `publish_to_telegram(queue_id)` — публикация объекта в Telegram чат
- `subscribe_to_chats_task(task_id)` — подписка на список чатов

**Обработчики очередей:**
- `process_autopublish()` — обработка очереди автопубликации (бот)
- `process_scheduled_publications()` — обработка запланированных публикаций
- `process_chat_subscriptions()` — обработка задач подписки на чаты
- `process_account_autopublish()` — обработка очередей публикаций аккаунтов
- `schedule_daily_autopublish()` — создание задач автопубликации на день

### 1.6 Стандарты логирования

**Файлы логов:**
- `logs/app.log` — все логи приложения (ротация 10MB, 10 файлов, DEBUG)
- `logs/errors.log` — только ошибки (ротация 5MB, 5 файлов, ERROR)
- `logs/test_app.log` — тестовые логи (очищаются при деплое, DEBUG)
- `logs/test_errors.log` — тестовые ошибки (очищаются при деплое, ERROR)
- `logs/test_database.log` — логи БД (SQL запросы, INFO)
- `logs/test_api.log` — логи API запросов (DEBUG)
- `logs/test_celery.log` — логи Celery задач (DEBUG)
- `logs/test_telethon.log` — логи Telethon (DEBUG)
- `logs/bot.log` — логи бота (DEBUG)
- `logs/bot_errors.log` — ошибки бота (ERROR)
- `logs/test_bot.log` — тестовые логи бота (DEBUG)
- `logs/test_bot_errors.log` — тестовые ошибки бота (ERROR)

**База данных:**
- Таблица `action_logs` — логи действий пользователей

**Формат логов:**
- Детальный: `%(asctime)s | %(levelname)-8s | %(name)-25s | %(funcName)-30s | %(lineno)-4d | %(message)s`
- Простой (консоль): `%(asctime)s | %(levelname)-8s | %(message)s`
- Уровни: DEBUG, INFO, WARNING, ERROR

### 1.7 Последние изменения логики
*Дата и суть последних изменений, причина (заполняется нейросетью после каждого значимого обновления)*

* `2026-02-20`: Исправление проблемы с автопубликацией от имени аккаунтов:
  - Исправлена синтаксическая ошибка в `process_account_autopublish` (строка 1045, 1048): неправильные отступы блоков `for account in accounts:` и `try:`
  - Исправлена обработка `SoftTimeLimitExceeded` в `process_account_autopublish`: обработчик вынесен наружу `app.app_context()` для перехвата исключения на любом этапе выполнения задачи
  - Добавлено детальное логирование в начале `process_account_autopublish`: логируются количество активных аккаунтов, готовых к публикации задач, проверка дубликатов
  - Создан скрипт диагностики `scripts/diagnose_account_autopublish.py` для проверки состояния `account_publication_queues` в БД (запуск: `docker exec -it realty_web python scripts/diagnose_account_autopublish.py`)
  - Создан скрипт для сброса застрявших задач `scripts/reset_stuck_account_queues.py` (запуск: `docker exec -it realty_web python scripts/reset_stuck_account_queues.py`)
  - Улучшена обработка застрявших задач: при `SoftTimeLimitExceeded` автоматически сбрасываются задачи в статусе 'processing' более 5 минут обратно в 'pending'
  - **КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ**: Исправлена проверка привязки чатов к аккаунтам в `create_or_update_autopublish_config` и `update_autopublish_config`: теперь проверяется и legacy связь через `chat.owner_account_id`, и новая связь через `TelegramAccountChat`. Это решает проблему, когда чаты не сохранялись в конфигурации автопубликации
  - **ИСПРАВЛЕНА ПРОБЛЕМА С ЗАБЫВАНИЕМ ЧАТОВ**: При переключении режима автопубликации с "Бот + Аккаунт" на "Бот" теперь сохраняется **ВСЯ** старая конфигурация полностью, включая чаты. Чаты не используются в режиме "Бот" (не создаются очереди для аккаунтов), но остаются в конфигурации. При повторном включении режима "Бот + Аккаунт" пользователь увидит те же аккаунты и чаты, что были выбраны ранее - ничего не нужно выбирать заново
  - Создана документация `ACCOUNT_PUBLICATION_GUIDE.md` с детальным описанием процесса публикации через аккаунты
  Причина: ни одна публикация от имени аккаунта не происходила, подозрение на проблему с `SoftTimeLimitExceeded` и неправильной проверкой привязки чатов к аккаунтам. Также чаты забывались при переключении режима автопубликации. Теперь исключение обрабатывается корректно на всех уровнях, добавлено детальное логирование для диагностики, исправлена проверка привязки чатов, исправлена проблема с забыванием чатов.

* `2026-02-19`: Исправления и улучшения:
  - Исправлены ошибки в `process_account_autopublish`: заменены прямые запросы на использование `app_db.session.query()` для корректной работы с транзакциями
  - Исправлена ошибка `ResourceClosedError` в `process_chat_subscriptions`: используется явный запрос через `app_db.session.query()` вместо `Model.query`
  - Добавлен выбор режима аккаунта (safe/normal/aggressive/smart/fix) на странице `/user/dashboard/telegram-accounts` с выпадающим списком
  - Создан скрипт `scripts/update_districts_from_html.py` для обновления районов из HTML файла
  - Добавлен поиск районов в компоненте `ObjectForm.tsx` с фильтрацией по введенному тексту
  - Исправлена проблема с выбором районов: теперь выбранные районы сохраняются при поиске
  - **УНИФИЦИРОВАНА БД**: Заменены все использования `bot.database` на `app.database` во всех файлах проекта (bot/, workers/, app/routes/). Теперь используется единая БД через `app.database.db.session` везде. `bot/database.py` оставлен для обратной совместимости, но теперь использует `app.database`.
  - Исправлены синтаксические ошибки в `app/routes/objects.py` и `workers/tasks.py` (неправильные отступы)
  - Исправлена публикация через аккаунты: в `process_account_autopublish` теперь используется `app_db.session` для работы с BotUser и BotObject внутри Flask контекста
  - Исправлена функция `_get_matching_bot_chats_for_object`: теперь принимает `db_session` вместо `db` для корректной работы
  - Исправлены ошибки отступов в `app/routes/objects.py` (строки 761-838), `workers/tasks.py` (строка 56, 274), `bot/utils.py` (строки 89-108), `app/routes/user_routes.py` (строки 211-260) - все синтаксические ошибки устранены
  Причина: исправление критических ошибок в Celery задачах, улучшение UX для управления аккаунтами и выбора районов, унификация БД для устранения дублирования и возможных race conditions, исправление проблем с публикацией через аккаунты, устранение синтаксических ошибок после унификации БД.
* `2026-02-18`: Рефакторинг очередей автопубликации:
  - Вынесен единый движок расписания с поддержкой 5 режимов (safe/normal/aggressive/smart/fix)
  - Унифицировано правило дубликатов через `duplicate_checker` (4 типа публикаций + переключатель для админов)
  - Обновлена логика распределения задач: сначала все чаты первого объекта, потом второго
  - Реализована ручная публикация через аккаунты с проверкой rate limiter
  - Добавлено поле `fix_interval_minutes` в модель `TelegramAccount`
  - Создан скрипт диагностики `scripts/check_queues.py`
  - Создан endpoint `POST /system/account-publications/manual` для ручной публикации
  Причина: необходимость унификации логики автопубликации для бота и аккаунтов, улучшение диагностики.
* `2024-12-20`: RULES2.MD выбран как единственный источник истины, все остальные .MD файлы удалены. Документ полностью обновлен согласно текущей реализации проекта.
* `2024-12-19`: Унифицирована система логирования, добавлено тотальное логирование во все критически точки. Причина: требование RULES1.md.

### 1.8 Активные проблемы / гипотезы
*Список известных проблем и путей их решения (обновляется нейросетью по мере обнаружения/решения)*

**КРИТИЧЕСКИЕ ПРОБЛЕМЫ:**

1. ~~**Дублирование моделей БД между app и bot**~~ ✅ РЕШЕНО
   - ~~Проблема: Модели дублируются в `app.models` и `bot.models`, используются разные подключения к БД (`app.database` и `bot.database`)~~
   - ~~Риск: Расхождение данных, сложность синхронизации, возможные race conditions~~
   - ✅ Решение: Унифицировано использование одной БД (`app.database`) везде. `bot.models` теперь импортирует модели из `app.models`, `bot.database` использует `app.database`.

2. **Legacy код и дублирование роутов**
   - Проблема: Существуют legacy роуты (`/system/admin/legacy`, `/system/dashboard/legacy`, `/system/logs/legacy`) наряду с новыми
   - Риск: Путаница, сложность поддержки, возможные устаревшие зависимости
   - Решение: Удалить legacy роуты после проверки, что они не используются

3. **Отсутствие валидации входных данных на бэкенде**
   - Проблема: Валидация телефонов только на фронтенде, на бэкенде минимальная проверка
   - Риск: Возможность отправки некорректных данных, SQL injection (хотя SQLAlchemy защищает), XSS
   - Решение: Добавить валидацию на бэкенде для всех входных данных

4. **Проблемы с обработкой ошибок Telethon**
   - Проблема: В `app/utils/telethon_client.py` возможны race conditions при одновременном доступе к сессиям, блокировки могут не работать корректно
   - Риск: Ошибки "database is locked", потеря данных сессий
   - Решение: Улучшить систему блокировок, добавить retry механизм

5. **Отсутствие транзакций в критических операциях**
   - Проблема: В некоторых местах (например, `workers/tasks.py`) операции с БД выполняются без явных транзакций
   - Риск: Частичное выполнение операций, несогласованность данных
   - Решение: Использовать транзакции для всех критических операций

6. **Проблемы с автопубликацией**
   - Проблема: В `schedule_daily_autopublish()` есть проблемы с обработкой ошибок, не учитываются интервалы аккаунтов при создании задач
   - Риск: Неправильное расписание публикаций, перегрузка аккаунтов
   - Решение: Улучшить логику расчета расписания, добавить проверку лимитов

7. **Отсутствие rate limiting на API**
   - Проблема: Нет rate limiting на Flask API endpoints (есть только для Telethon)
   - Риск: DDoS атаки, перегрузка сервера
   - Решение: Добавить rate limiting для всех API endpoints

8. **Проблемы с обработкой файлов**
   - Проблема: Загрузка файлов без проверки размера, типа, возможны path traversal атаки
   - Риск: Переполнение диска, выполнение вредоносного кода
   - Решение: Добавить валидацию размера, типа файлов, sanitize имена файлов

9. **Отсутствие индексов в БД**
   - Проблема: Некоторые поля, используемые в WHERE и JOIN, не имеют индексов
   - Риск: Медленные запросы при росте данных
   - Решение: Добавить индексы для часто используемых полей

10. **Проблемы с часовыми поясами**
    - Проблема: Смешение UTC и МСК времени в разных местах кода
    - Риск: Неправильное время публикаций, путаница в логах
    - Решение: Унифицировать использование timezone utils

11. **Отсутствие мониторинга ошибок**
    - Проблема: Нет централизованного мониторинга ошибок (Sentry, Rollbar)
    - Риск: Критические ошибки могут остаться незамеченными
    - Решение: Добавить интеграцию с системой мониторинга ошибок

12. **Проблемы с безопасностью JWT**
    - Проблема: JWT токены не имеют refresh механизма, нет проверки на отзыв токенов
    - Риск: Компрометация токенов, невозможность отозвать доступ
    - Решение: Добавить refresh tokens, blacklist для отозванных токенов

13. **Отсутствие тестов**
    - Проблема: Нет unit тестов, integration тестов
    - Риск: Регрессии при изменениях, сложность рефакторинга
    - Решение: Добавить тесты для критических компонентов

14. **Проблемы с обработкой больших объемов данных**
    - Проблема: Нет пагинации в некоторых endpoints, загрузка всех данных в память
    - Риск: Перегрузка сервера, медленные ответы
    - Решение: Добавить пагинацию везде, использовать streaming для больших данных

15. **Отсутствие документации API**
    - Проблема: Нет Swagger/OpenAPI документации
    - Риск: Сложность интеграции, непонимание API
    - Решение: Добавить Swagger документацию

16. **Проблемы с конфигурацией**
    - Проблема: Секретные ключи могут быть в коде, нет валидации переменных окружения
    - Риск: Утечка секретов, неправильная конфигурация
    - Решение: Использовать только переменные окружения, добавить валидацию при старте

17. **Отсутствие backup стратегии**
    - Проблема: Нет автоматических бэкапов БД
    - Риск: Потеря данных при сбоях
    - Решение: Настроить автоматические бэкапы PostgreSQL

18. **Проблемы с логированием чувствительных данных**
    - Проблема: В логах могут попадать пароли, токены, персональные данные
    - Риск: Утечка конфиденциальной информации
    - Решение: Добавить фильтрацию чувствительных данных в логах

19. **TODO в коде**
    - `bot/main.py:237` — TODO: Port all handlers from botOLD.py
    - `bot/handlers_object_edit.py:839` — TODO: Implement media handling
    - `app/routes/publications.py:85` — TODO: Add to Celery queue
    - `app/routes/objects.py:271-272` — TODO: Extract region/city from districts
    - `templates/admin/bot_chats.html:286` — TODO: Implement edit modal

20. **Проблемы с обработкой ошибок Celery**
    - Проблема: Некоторые ошибки в Celery задачах не логируются должным образом
    - Риск: Потеря информации об ошибках, сложность диагностики
    - Решение: Улучшить обработку ошибок во всех Celery задачах

---

## 2. 📋 Бэклог задач (текущие и предстоящие работы)

*Здесь вы пишете новые требования, а нейросеть отмечает выполненные и добавляет подзадачи.*  
Формат:  
`[ ] Приоритет: Описание задачи (дата добавления)`  
`[x] Приоритет: Описание задачи (дата выполнения) — кем выполнено`

Задачи:
* [x] HIGH: Реализовать тотальное логирование в боте (2024-12-19) — нейросеть
* [ ] MEDIUM: Добавить метрики для количества публикаций (2024-12-20)
* [x] HIGH: Создать скрипт для проверки БД (autopublish_configs, account_publication_queues) (2026-02-18) — нейросеть
* [x] HIGH: Исправить ошибки в process_account_autopublish и process_chat_subscriptions (2026-02-19) — нейросеть
* [x] HIGH: Добавить выбор режима аккаунта на странице telegram-accounts (2026-02-19) — нейросеть
* [x] HIGH: Создать скрипт для обновления районов из HTML (2026-02-19) — нейросеть
* [x] HIGH: Добавить поиск районов в компоненте выбора (2026-02-19) — нейросеть
* [x] HIGH: Унифицировать использование одной БД и одного набора моделей (2026-02-19) — нейросеть
* [x] HIGH: Исправить проблемы с публикацией через аккаунты (2026-02-19) — нейросеть
* [x] HIGH: Вынести движок расписания в единую утилиту (8:00-22:00 МСК, 5 режимов интервалов) (2026-02-18) — нейросеть
* [x] HIGH: Унифицировать правило дубликатов (4 переключателя: ручная бот, ручная акк, авто бот, авто акк + для админа) (2026-02-18) — нейросеть
* [x] HIGH: Разделить создание и обработку задач (schedule_daily_autopublish и process_account_autopublish) (2026-02-18) — нейросеть
* [x] HIGH: Реализовать ручную публикацию через аккаунты с проверкой rate limiter (2026-02-18) — нейросеть
* [x] HIGH: Обновить логику распределения задач: сначала все чаты первого объекта, потом второго и т.д. (2026-02-18) — нейросеть
* [x] HIGH: Исправить обработку SoftTimeLimitExceeded в process_account_autopublish (2026-02-20) — нейросеть
* [x] HIGH: Создать скрипт диагностики для проверки account_publication_queues в БД (2026-02-20) — нейросеть
* [x] HIGH: Добавить детальное логирование в process_account_autopublish для отслеживания выполнения (2026-02-20) — нейросеть
* [x] HIGH: Исправить проверку привязки чатов к аккаунтам в create_or_update_autopublish_config (2026-02-20) — нейросеть
* [x] HIGH: Создать документацию по публикации через аккаунты (2026-02-20) — нейросеть

**Правила ведения бэклога:**
- Вы можете добавлять задачи в любой момент.
- Нейросеть, начиная работу, проверяет бэклог и может предложить взять следующую задачу или уточнить её.
- После выполнения задачи нейросеть помечает её как `[x]`, переносит детали в раздел 1.7 (Последние изменения) и, если нужно, добавляет новые подзадачи.

---

## 3. 🗄️ Миграции базы данных (Alembic)

### 3.1 Критическое правило: предотвращение Multiple Head
⚠️ **Никогда не создавай две миграции с одинаковым `down_revision`!**  
Подробные инструкции по проверке и линеаризации — в [исходной версии](#).  
*При каждом создании миграции нейросеть обязана выполнить проверку `alembic heads`.*

---

## 4. 📜 История изменений ЭТОГО ФАЙЛА

*Дата и суть изменений, внесённых в сам `RULES2.MD` (заполняется нейросетью или пользователем)*

* `2024-12-20`: 
  - RULES2.MD выбран как единственный источник истины для проекта
  - Удалены все остальные .MD файлы из проекта (23 файла)
  - Полностью обновлен раздел 1 "Текущее состояние проекта":
    - Добавлено детальное описание архитектуры (1.2)
    - Добавлено описание всех 16 моделей БД (1.3)
    - Добавлено описание всех API endpoints (1.4)
    - Добавлено описание Celery задач (1.5)
    - Расширено описание логирования (1.6)
  - Добавлен раздел 1.8 "Активные проблемы / гипотезы" с 20 выявленными проблемами в текущей реализации
  - Обновлена история изменений (1.7)
* `2024-12-20`: Добавлен раздел «Бэклог задач», уточнены правила обновления динамической части.
* `2024-12-19`: Первоначальная версия.

---

## ⚠️ Важно
Все неизменные правила поведения нейросети (роль, принципы, формат ответов, тестирование, логирование, архитектурные требования компактности) теперь находятся в файле `.cursorrules` в корне проекта.  
Данный файл содержит только динамическую информацию о проекте.