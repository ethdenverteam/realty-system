# Инструкция по добавлению админа

## Способ 1: Через API (рекомендуется)

Используйте новый эндпоинт API для добавления админа:

```bash
POST /admin/dashboard/users/add-admin-by-telegram-id
Content-Type: application/json
Authorization: Bearer <your_jwt_token>

{
  "telegram_id": 189397952
}
```

Или через curl:
```bash
curl -X POST http://your-domain/api/admin/dashboard/users/add-admin-by-telegram-id \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"telegram_id": 189397952}'
```

## Способ 2: Через скрипт (в контейнере)

Запустите скрипт внутри контейнера приложения:

```bash
# Войти в контейнер
docker exec -it realty_app python scripts/add_admin.py 189397952

# Или через docker-compose
docker-compose exec app python scripts/add_admin.py 189397952
```

## Способ 3: Через SQL (прямо в БД)

Если нужно добавить напрямую в базу данных:

```sql
-- Найти пользователя
SELECT * FROM users WHERE telegram_id = 189397952;

-- Если пользователь существует, обновить роль
UPDATE users SET web_role = 'admin' WHERE telegram_id = 189397952;

-- Если пользователя нет, создать нового
INSERT INTO users (telegram_id, web_role, bot_role, created_at, last_activity)
VALUES (189397952, 'admin', 'premium', NOW(), NOW());
```

## Проверка

После добавления админа, пользователь должен:
1. Войти в веб-интерфейс через код из бота
2. Увидеть админ панель и иметь доступ ко всем админ функциям

---

**Telegram ID для добавления:** 189397952

