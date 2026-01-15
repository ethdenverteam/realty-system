# Пошаговая настройка Git для синхронизации

## Шаг 1: Создайте репозиторий на GitHub

1. Зайдите на https://github.com
2. Нажмите "New repository"
3. Название: `realty-system` (или любое другое)
4. **НЕ** добавляйте README, .gitignore, лицензию (у нас уже есть)
5. Нажмите "Create repository"
6. Скопируйте URL репозитория (например: `https://github.com/your-username/realty-system.git`)

## Шаг 2: Настройка на сервере

```bash
# Подключитесь к серверу по SSH
ssh user@your-server-ip

# Перейдите в папку проекта
cd /path/to/realty-system

# Инициализируйте Git
git init

# Настройте имя и email (если еще не сделано)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Добавьте все файлы
git add .

# Создайте первый коммит
git commit -m "Initial project setup"

# Добавьте удаленный репозиторий (замените URL на ваш)
git remote add origin https://github.com/your-username/realty-system.git

# Отправьте код на GitHub
git branch -M main
git push -u origin main
```

## Шаг 3: Настройка локально (в Cursor)

### Вариант А: Если у вас уже есть папка webbotreal

```bash
# Откройте терминал в Cursor (Ctrl+`)
# Перейдите в папку проекта
cd C:\Сore\Code\WebBotReal

# Инициализируйте Git (если еще не сделано)
git init

# Добавьте удаленный репозиторий
git remote add origin https://github.com/your-username/realty-system.git

# Получите код с GitHub
git pull origin main --allow-unrelated-histories

# Если возникли конфликты, разрешите их, затем:
git add .
git commit -m "Merge with remote"
git push origin main
```

### Вариант Б: Клонировать заново (проще)

```bash
# В терминале Cursor
cd C:\Сore\Code

# Удалите или переименуйте старую папку (если нужно)
# Переименуйте: ren WebBotReal WebBotReal_old

# Клонируйте репозиторий
git clone https://github.com/your-username/realty-system.git

# Откройте папку realty-system в Cursor
```

## Шаг 4: Проверка синхронизации

### На сервере:
```bash
cd /path/to/realty-system
echo "# Test" >> test.txt
git add test.txt
git commit -m "Test commit"
git push origin main
```

### Локально:
```bash
cd C:\Сore\Code\realty-system
git pull origin main
# Должен появиться файл test.txt
```

## Где выполнять команды Docker?

**ВСЕ команды Docker выполняются НА СЕРВЕРЕ**, где установлен Docker:

```bash
# На сервере через SSH:
ssh user@your-server-ip
cd /path/to/realty-system

# Затем команды Docker:
docker-compose up -d
docker-compose exec web alembic upgrade head
```

**НЕ выполняйте команды Docker локально** - они будут искать Docker на вашем Windows компьютере.

## Рекомендуемый workflow

1. **Работаете в Cursor** → делаете изменения → `git commit` → `git push`
2. **На сервере** → `git pull` → перезапускаете контейнеры если нужно
3. **Если что-то меняли на сервере** → `git commit` → `git push`
4. **В Cursor** → `git pull` → получаете изменения

## Важно!

- Файл `.env` НЕ должен попадать в Git (уже в `.gitignore`)
- Создайте `.env` отдельно на сервере и локально
- Не коммитьте пароли и токены

