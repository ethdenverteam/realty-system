# Команды для проверки логов и диагностики 502 ошибки

## Важно: имя сервиса - `web`, а не `app`!

### 1. Проверить логи веб-приложения (правильная команда):

```bash
# Если используете docker-compose (старая версия с дефисом):
docker-compose logs web --tail=100

# Если используете docker compose (новая версия без дефиса):
docker compose logs web --tail=100

# Или напрямую через docker:
docker logs realty_web --tail=100
```

### 2. Проверить логи nginx:

```bash
docker-compose logs nginx --tail=50
# или
docker logs realty_nginx --tail=50
```

### 3. Проверить статус контейнеров:

```bash
docker ps -a | grep realty
```

### 4. Перезапустить контейнер web:

```bash
# Перейти в директорию с docker-compose.yml
cd /path/to/realty-system

# Перезапустить только web сервис
docker-compose restart web
# или
docker compose restart web
```

### 5. Проверить, запущен ли контейнер:

```bash
docker ps | grep realty_web
```

### 6. Если контейнер не запущен, посмотреть последние логи перед падением:

```bash
docker logs realty_web --tail=200
```

### 7. Попробовать запустить контейнер заново:

```bash
cd /path/to/realty-system
docker-compose up -d web
# или
docker compose up -d web
```

### 8. Проверить ошибки импорта Python напрямую в контейнере:

```bash
docker exec -it realty_web python -c "from app.config import Config; print('Config OK')"
docker exec -it realty_web python -c "from app.utils.time_utils import get_moscow_time; print('time_utils OK')"
```

### 9. Проверить синтаксис Python файлов в контейнере:

```bash
docker exec -it realty_web python -m py_compile app/config.py
docker exec -it realty_web python -m py_compile app/utils/time_utils.py
```

