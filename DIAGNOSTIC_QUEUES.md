# Инструкция по диагностике очередей автопубликации

## 1. Проверка контейнеров Celery

```bash
# Проверить статус контейнеров
docker compose ps

# Если celery_worker или celery_beat перезапускаются (Restarting):
# Смотрим логи для выяснения причины
docker logs realty_celery_worker --tail 100
docker logs realty_celery_beat --tail 100
```

## 2. Проверка БД через скрипт

```bash
# Проверить все очереди
docker exec -it realty_web python scripts/check_queues.py

# Проверить конкретный объект
docker exec -it realty_web python scripts/check_queues.py AAA052

# Проверить конкретный объект и аккаунт
docker exec -it realty_web python scripts/check_queues.py AAA052 +79996731791
```

## 3. Проверка БД через SQL (psql)

```bash
# Подключиться к БД
docker exec -it realty_postgres psql -U realty_user -d realty_db

# Проверить конфигурацию автопубликации для объекта
SELECT * FROM autopublish_configs WHERE object_id = 'AAA052';

# Проверить очереди бота
SELECT queue_id, object_id, chat_id, status, scheduled_time, error_message 
FROM publication_queues 
WHERE object_id = 'AAA053' AND type = 'bot' AND mode = 'autopublish'
ORDER BY scheduled_time;

# Проверить очереди аккаунтов
SELECT aq.queue_id, aq.object_id, aq.chat_id, aq.account_id, aq.status, 
       aq.scheduled_time, aq.error_message, ta.phone, ta.mode, ta.is_active
FROM account_publication_queues aq
JOIN telegram_accounts ta ON aq.account_id = ta.account_id
WHERE aq.object_id = 'AAA053'
ORDER BY aq.account_id, aq.scheduled_time;

# Проверить аккаунт
SELECT * FROM telegram_accounts WHERE phone = '+79996731791';

# Проверить историю публикаций
SELECT * FROM publication_history 
WHERE object_id = 'AAA053' 
ORDER BY published_at DESC 
LIMIT 10;
```

## 4. Ручной запуск задач Celery

```bash
# Правильное имя контейнера: realty_celery_worker (не realty_worker!)

# Запустить обработку очереди бота
docker exec -it realty_celery_worker celery -A workers.celery_app call workers.tasks.process_autopublish

# Запустить обработку очередей аккаунтов
docker exec -it realty_celery_worker celery -A workers.celery_app call workers.tasks.process_account_autopublish

# Запустить создание задач на день
docker exec -it realty_celery_worker celery -A workers.celery_app call workers.tasks.schedule_daily_autopublish
```

## 5. Проверка логов

```bash
# Логи Celery
docker logs realty_celery_worker --tail 200 -f

# Логи приложения
docker logs realty_web --tail 200 -f

# Логи Telethon
tail -f logs_server/test_telethon.log

# Логи ошибок
tail -f logs_server/test_errors.log
```

## 6. Типичные проблемы

### Проблема: celery_worker перезапускается
**Причина:** Ошибка при импорте модулей или подключении к БД/Redis
**Решение:** 
```bash
docker logs realty_celery_worker --tail 100
# Ищи ошибки типа ImportError, ConnectionError, DatabaseError
```

### Проблема: Задачи не создаются в account_publication_queues
**Причина:** 
- Аккаунт неактивен (`is_active = false`)
- Аккаунт не указан в `accounts_config_json`
- Объект в статусе "архив"
**Решение:** Проверить через SQL (см. п.3)

### Проблема: Задачи созданы, но не обрабатываются
**Причина:**
- `scheduled_time` в будущем
- Аккаунт деактивирован из-за FloodWait
- Rate limiter блокирует отправку
**Решение:** 
```bash
# Проверить статусы задач
SELECT status, COUNT(*) FROM account_publication_queues GROUP BY status;

# Проверить аккаунт
SELECT account_id, phone, is_active, last_error FROM telegram_accounts;
```

