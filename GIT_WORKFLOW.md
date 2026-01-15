# Рабочий процесс с Git

## Начальная настройка

### 1. На сервере (Ubuntu)

```bash
# Перейдите в папку проекта
cd /path/to/realty-system

# Инициализируйте Git (если еще не сделано)
git init

# Добавьте все файлы
git add .

# Создайте первый коммит
git commit -m "Initial commit"

# Добавьте удаленный репозиторий (GitHub/GitLab)
git remote add origin https://github.com/your-username/realty-system.git

# Отправьте код на GitHub
git push -u origin main
```

### 2. Локально (Windows/Cursor)

```bash
# Переименуйте папку если нужно (опционально)
# В FileZilla или через проводник

# Клонируйте репозиторий
git clone https://github.com/your-username/realty-system.git

# Или если уже есть папка с кодом:
cd webbotreal
git init
git remote add origin https://github.com/your-username/realty-system.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

## Ежедневная работа

### Когда работаете ЛОКАЛЬНО (в Cursor):

```bash
# 1. Получите последние изменения с сервера
git pull origin main

# 2. Внесите изменения в Cursor
# ... редактируете файлы ...

# 3. Сохраните изменения в Git
git add .
git commit -m "Описание изменений"
git push origin main
```

### Когда работаете на СЕРВЕРЕ:

```bash
# 1. Перейдите в папку проекта
cd /path/to/realty-system

# 2. Получите изменения с GitHub
git pull origin main

# 3. Если что-то изменили на сервере
git add .
git commit -m "Изменения на сервере"
git push origin main
```

## Важные моменты

1. **Всегда делайте `git pull` перед началом работы** - чтобы получить последние изменения
2. **Коммитьте часто** - после каждого логического изменения
3. **Пишите понятные сообщения коммитов** - "Добавлена авторизация", "Исправлена ошибка в боте"
4. **Не коммитьте `.env` файл** - он уже в `.gitignore`

## Если возникли конфликты

```bash
# Git покажет конфликтующие файлы
# Откройте их в редакторе, найдите строки с <<<<<<< ======= >>>>>>>
# Выберите нужную версию кода
# Сохраните файл

# Затем:
git add .
git commit -m "Разрешен конфликт"
git push origin main
```

## Полезные команды

```bash
# Посмотреть статус изменений
git status

# Посмотреть историю коммитов
git log --oneline

# Отменить локальные изменения (если что-то сломалось)
git checkout -- filename

# Посмотреть различия
git diff
```

