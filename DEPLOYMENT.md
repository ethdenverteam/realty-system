# Инструкция по развертыванию

## Подготовка сервера

### 1. Установка Docker и Docker Compose

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo apt install docker-compose-plugin -y

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Клонирование проекта

```bash
git clone <repository-url>
cd realty-system
```

### 3. Настройка переменных окружения

```bash
cp .env.example .env
nano .env
```

Обязательно измените:
- `POSTGRES_PASSWORD` - надежный пароль для БД
- `JWT_SECRET_KEY` - случайная строка для JWT
- `TELEGRAM_BOT_TOKEN` - токен вашего бота
- `ADMIN_ID` - ваш Telegram ID

### 4. Запуск контейнеров

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Проверка статуса
docker-compose ps
```

### 5. Инициализация базы данных

```bash
# Создание начальной миграции
docker-compose exec web alembic revision --autogenerate -m "Initial migration"

# Применение миграций
docker-compose exec web alembic upgrade head
```

### 6. Настройка SSL (опционально)

```bash
# Установка Certbot
sudo apt install certbot -y

# Получение сертификата
sudo certbot certonly --standalone -d your-domain.com

# Копирование сертификатов
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem

# Раскомментировать HTTPS секцию в nginx/nginx.conf
# Перезапуск nginx
docker-compose restart nginx
```

## Обслуживание

### Обновление кода

```bash
git pull
docker-compose build
docker-compose up -d
docker-compose exec web alembic upgrade head
```

### Бэкап базы данных

```bash
# Создание бэкапа
docker-compose exec postgres pg_dump -U realty_user realty_db > backup_$(date +%Y%m%d).sql

# Восстановление
docker-compose exec -T postgres psql -U realty_user realty_db < backup_20240101.sql
```

### Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f web
docker-compose logs -f bot
docker-compose logs -f celery_worker
```

### Перезапуск сервисов

```bash
# Все сервисы
docker-compose restart

# Конкретный сервис
docker-compose restart web
docker-compose restart bot
```

## Мониторинг

- **Grafana**: http://your-domain:3000 (admin/admin)
- **Prometheus**: http://your-domain:9090
- **Portainer**: http://your-domain:9000 (если установлен)

## Устранение неполадок

### Проблемы с подключением к БД

```bash
# Проверка статуса PostgreSQL
docker-compose exec postgres pg_isready

# Проверка подключения
docker-compose exec web python -c "from app.database import db; print(db)"
```

### Проблемы с Redis

```bash
# Проверка Redis
docker-compose exec redis redis-cli ping
```

### Очистка и пересоздание

```bash
# Остановка и удаление контейнеров
docker-compose down

# Удаление volumes (ВНИМАНИЕ: удалит все данные!)
docker-compose down -v

# Пересоздание
docker-compose up -d --build
```

