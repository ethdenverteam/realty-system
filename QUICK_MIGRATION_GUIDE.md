# Быстрая инструкция по миграции

## Проблема
Вы получили ошибку:
```
docker-compose exec app alembic upgrade head
no configuration file provided: not found
```

## Решение

### ✅ Правильная команда (используйте `web` вместо `app`):

```bash
docker-compose exec web sh -c "cd /app && alembic upgrade head"
```

### Альтернативные варианты:

**Вариант 1: Через docker exec**
```bash
docker exec -it -w /app realty_web alembic upgrade head
```

**Вариант 2: Войти в контейнер**
```bash
docker-compose exec web bash
cd /app
alembic upgrade head
exit
```

**Вариант 3: Если миграция не работает, выполните SQL напрямую**
```bash
# Войти в PostgreSQL
docker-compose exec postgres psql -U realty_user -d realty_db

# Выполнить SQL
ALTER TABLE chats ADD COLUMN IF NOT EXISTS cached_at TIMESTAMP;
\q
```

## Проверка результата

После выполнения проверьте:
```bash
docker-compose exec web sh -c "cd /app && alembic current"
```

Должна быть видна версия: `add_chat_cached_at`

## Почему `web`, а не `app`?

В вашем `docker-compose.yml` сервис называется `web`:
```yaml
web:
  container_name: realty_web
  ...
```

Поэтому используйте `docker-compose exec web`, а не `docker-compose exec app`.

