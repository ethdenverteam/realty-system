#!/bin/bash
# Скрипт для выполнения миграции базы данных

echo "Выполнение миграции базы данных..."

# Вариант 1: Через docker-compose (рекомендуется)
docker-compose exec -T web sh -c "cd /app && alembic upgrade head"

# Если не работает, попробуйте:
# docker exec -it -w /app realty_web alembic upgrade head

echo "Миграция завершена!"

