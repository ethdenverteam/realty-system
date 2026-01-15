# Быстрый старт

## Что делать СЕЙЧАС

### 1. Создайте репозиторий на GitHub
- Зайдите на github.com
- Создайте новый репозиторий (название: `realty-system`)
- Скопируйте URL

### 2. На сервере (через SSH)

```bash
# Подключитесь к серверу
ssh user@your-server-ip

# Перейдите в папку проекта
cd /path/to/realty-system

# Инициализируйте Git
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/realty-system.git
git branch -M main
git push -u origin main
```
Ethdenver111
### 3. Локально (в Cursor)

```bash
# Вариант 1: Если хотите переименовать папку
cd C:\Сore\Code
ren WebBotReal realty-system
cd realty-system

# Вариант 2: Или клонируйте заново
cd C:\Сore\Code
git clone https://github.com/your-username/realty-system.git
cd realty-system
```

Затем в Cursor:
```bash
# Добавьте удаленный репозиторий (если не клонировали)
git remote add origin https://github.com/your-username/realty-system.git
git pull origin main --allow-unrelated-histories
```

### 4. Настройте .env файлы

**На сервере:**
```bash
cd /path/to/realty-system
nano .env
# Заполните все переменные
```

**Локально:**
```bash
# В Cursor
# Скопируйте .env.example в .env
# Заполните значениями (можно теми же что на сервере, кроме DATABASE_URL)
```

### 5. Запуск на сервере

```bash
# На сервере через SSH:
cd /path/to/realty-system

# Запустите контейнеры
docker-compose up -d

# Подождите 30 секунд, затем инициализируйте БД
docker-compose exec web alembic revision --autogenerate -m "Initial migration"
docker-compose exec web alembic upgrade head

# Проверьте статус
docker-compose ps
docker-compose logs -f
```

## Ежедневная работа

### Когда работаете в Cursor:

1. Откройте терминал (Ctrl+`)
2. `git pull` - получите последние изменения
3. Редактируйте файлы
4. `git add .`
5. `git commit -m "Описание"`
6. `git push`

### Когда нужно обновить на сервере:

```bash
# На сервере:
cd /path/to/realty-system
git pull
docker-compose restart web  # или bot, или все: docker-compose restart
```

## Важные команды

```bash
# Посмотреть что изменилось
git status

# Посмотреть различия
git diff

# Отменить локальные изменения (если что-то сломалось)
git checkout -- filename

# Получить изменения с сервера
git pull origin main

# Отправить изменения на сервер
git push origin main
```

## Где выполнять команды?

- **Git команды** - можно и локально, и на сервере
- **Docker команды** - ТОЛЬКО на сервере (где установлен Docker)
- **Редактирование кода** - в Cursor локально

## Если что-то пошло не так

```bash
# Отменить последний коммит (но сохранить изменения)
git reset --soft HEAD~1

# Посмотреть историю
git log --oneline

# Вернуться к определенному коммиту
git checkout <commit-hash>
```

