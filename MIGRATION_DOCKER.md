# Выполнение миграции в Docker

## Проблема
При выполнении `docker-compose exec app alembic upgrade head` возникает ошибка "no configuration file provided: not found"

## Решение

### Вариант 1: Использовать правильное имя сервиса (рекомендуется)

В вашем `docker-compose.yml` сервис называется `web`, а не `app`:

```bash
docker-compose exec web alembic upgrade head
```

### Вариант 2: Указать рабочую директорию явно

```bash
docker-compose exec web sh -c "cd /app && alembic upgrade head"
```

### Вариант 3: Войти в контейнер и выполнить команду

```bash
# Войти в контейнер
docker-compose exec web bash

# Внутри контейнера
cd /app
alembic upgrade head
exit
```

### Вариант 4: Выполнить через docker exec напрямую

```bash
docker exec -it realty_web alembic upgrade head
```

или с указанием рабочей директории:

```bash
docker exec -it -w /app realty_web alembic upgrade head
```

## Проверка

После выполнения миграции проверьте:

```bash
# Проверить текущую версию миграции
docker-compose exec web alembic current

# Или
docker exec -it -w /app realty_web alembic current
```

Должна быть видна версия `add_chat_cached_at`.

## Если все еще не работает

1. Проверьте, что файл `alembic.ini` существует в корне проекта
2. Проверьте, что папка `migrations` существует
3. Проверьте логи контейнера:
   ```bash
   docker-compose logs web
   ```

## Альтернатива: Выполнить миграцию через Python

Если alembic все еще не работает, можно выполнить миграцию напрямую через SQL:

```bash
# Войти в PostgreSQL контейнер
docker-compose exec postgres psql -U realty_user -d realty_db

# Выполнить SQL
ALTER TABLE chats ADD COLUMN IF NOT EXISTS cached_at TIMESTAMP;
\q
```

Но лучше использовать alembic для правильного отслеживания версий.

