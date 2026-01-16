# Синхронизация логов с сервера

Этот инструмент позволяет синхронизировать логи с сервера в локальный проект для анализа AI.

## ⭐ РЕКОМЕНДУЕМЫЙ СПОСОБ: Скачивание через веб-интерфейс

Самый простой способ получить логи:

1. Откройте админ-панель → **Просмотр логов** (`/admin/dashboard/logs`)
2. Нажмите кнопку **"⬇️ Скачать логи"**
3. Браузер скачает ZIP архив со всеми логами
4. Распакуйте архив в папку `logs_server/` в корне проекта:

```bash
# Распакуйте realty_logs_YYYYMMDD_HHMMSS.zip в:
realty-system/
  └── logs_server/
      ├── app.log
      ├── errors.log
      ├── bot.log
      └── bot_errors.log
```

**Готово!** Теперь AI может анализировать логи из `logs_server/`.

---

## ⭐⭐⭐ ЛУЧШИЙ СПОСОБ: Автоматическое скачивание через скрипт

Для автоматического скачивания логов напрямую в папку `logs_server/` используйте скрипт:

### Python скрипт (рекомендуется)

```bash
# Базовое использование (попросит токен)
python download_logs.py

# С параметрами
python download_logs.py https://your-domain.com YOUR_API_TOKEN

# Через переменные окружения
export REALTY_API_URL="https://your-domain.com"
export REALTY_API_TOKEN="your_token_here"
python download_logs.py
```

### PowerShell скрипт (Windows)

```powershell
# Базовое использование
.\download_logs.ps1

# С параметрами
.\download_logs.ps1 -ApiUrl "https://your-domain.com" -ApiToken "YOUR_TOKEN"
```

### Получение API токена

1. Зайдите в админ-панель (`/admin/dashboard`)
2. Откройте DevTools (F12) → Console
3. Выполните: `localStorage.getItem('jwt_token')`
4. Скопируйте токен

Или создайте файл `.api_token` в корне проекта с токеном (файл в .gitignore).

### Настройка (опционально)

Создайте `.api_token` файл в корне проекта:
```
your_jwt_token_here
```

Или установите переменные окружения:
```bash
# Windows PowerShell
$env:REALTY_API_URL = "https://your-domain.com"
$env:REALTY_API_TOKEN = "your_token"

# Linux/Mac
export REALTY_API_URL="https://your-domain.com"
export REALTY_API_TOKEN="your_token"
```

---

## Альтернативные способы

## Зачем это нужно?

- **Прямой доступ AI к логам**: AI (нейросеть) в Cursor может сразу анализировать актуальные логи
- **Локальная работа**: Не нужно копировать логи вручную
- **Автоматизация**: Можно настроить автоматическую синхронизацию

## Варианты синхронизации

### Вариант 1: Python скрипт (рекомендуется) ⭐

Работает на Windows и Linux:

```bash
# Базовое использование (с настройками по умолчанию)
python sync_logs.py

# С указанием сервера
python sync_logs.py root msk-1-vm-vgtr ~/realty-system/logs
```

**Преимущества:**
- Работает на всех ОС
- Автоматически выбирает лучший метод (rsync/scp)
- Проверяет наличие инструментов

### Вариант 2: Bash скрипт (Linux/Mac/WSL)

```bash
# Дать права на выполнение
chmod +x sync_logs.sh

# Запустить
./sync_logs.sh root@msk-1-vm-vgtr

# Или с явными параметрами
./sync_logs.sh root msk-1-vm-vgtr ~/realty-system/logs
```

### Вариант 3: PowerShell (Windows)

```powershell
# Базовое использование
.\sync_logs.ps1

# С параметрами
.\sync_logs.ps1 -ServerUser root -ServerHost msk-1-vm-vgtr -ServerPath ~/realty-system/logs
```

## Настройка

### 1. Настройте сервер в скрипте

Откройте `sync_logs.py` и измените значения по умолчанию:

```python
DEFAULT_SERVER_USER = "root"
DEFAULT_SERVER_HOST = "your-server.com"  # <-- Измените это
DEFAULT_SERVER_PATH = "~/realty-system/logs"
```

### 2. Настройте SSH доступ

Убедитесь, что у вас настроен SSH доступ к серверу:

```bash
# Проверьте подключение
ssh root@your-server.com

# Если нужно, добавьте SSH ключ
ssh-copy-id root@your-server.com
```

### 3. Установите необходимые инструменты

**Для rsync (рекомендуется):**
- Linux/Mac: `sudo apt install rsync` или `brew install rsync`
- Windows: Используйте WSL или установите через Git Bash

**Для scp (альтернатива):**
- Обычно входит в состав OpenSSH (установлен по умолчанию на Linux/Mac)
- Windows: Установите OpenSSH через "Параметры Windows" → "Приложения" → "Возможности"

## Использование

### Ручная синхронизация

Просто запустите скрипт когда нужно:

```bash
python sync_logs.py
```

Логи будут скопированы в папку `logs_server/` в корне проекта.

### Автоматическая синхронизация

#### Вариант A: Git Hook (при коммите)

Создайте файл `.git/hooks/pre-commit`:

```bash
#!/bin/bash
python sync_logs.py
```

#### Вариант B: Cron/Task Scheduler

**Linux/Mac (cron):**
```bash
# Редактировать cron
crontab -e

# Добавить (синхронизация каждые 5 минут)
*/5 * * * * cd /path/to/realty-system && python sync_logs.py
```

**Windows (Task Scheduler):**
1. Откройте "Планировщик заданий"
2. Создайте новое задание
3. Триггер: повторять каждые 5 минут
4. Действие: Запустить `python sync_logs.py` в директории проекта

#### Вариант C: Watch скрипт (автоматическая синхронизация при изменениях)

```bash
# Linux (требует inotify-tools)
watch -n 60 'python sync_logs.py'

# Или используйте fswatch (Mac) или FileSystemWatcher (Python)
```

## Результат

После синхронизации логи будут в папке:
```
realty-system/
  └── logs_server/
      ├── app.log
      ├── errors.log
      ├── bot.log
      └── bot_errors.log
```

**Важно:** Папка `logs_server/` автоматически добавлена в `.gitignore`, чтобы логи не попадали в git.

## AI может анализировать логи

После синхронизации просто укажите AI на файлы в `logs_server/`:

```
@logs_server/errors.log - проанализируй последние ошибки
```

Или AI автоматически увидит логи при анализе ошибок, если вы упомяните проблемы.

## Устранение проблем

### Ошибка подключения SSH

```
❌ Error: Permission denied (publickey)
```

**Решение:** Настройте SSH ключи или используйте пароль:
```bash
ssh-copy-id user@server
```

### Команда не найдена

```
❌ Error: rsync: command not found
```

**Решение:** Установите rsync или используйте scp (скрипт автоматически переключится).

### Путь не найден

```
❌ Error: No such file or directory
```

**Решение:** Проверьте путь на сервере:
```bash
ssh user@server "ls -la ~/realty-system/logs"
```

## Безопасность

- Логи могут содержать чувствительную информацию
- Папка `logs_server/` в `.gitignore` - логи не попадут в git
- Используйте SSH ключи вместо паролей
- Ограничьте доступ к папке `logs_server/` на локальной машине

## Альтернативные варианты

Если синхронизация не подходит, можно:

1. **Копировать вручную** через SFTP клиент (FileZilla, WinSCP)
2. **Использовать веб-интерфейс** - логи доступны через `/admin/dashboard/logs`
3. **Настроить CI/CD** - автоматическая синхронизация при деплое
4. **Монтировать через SSHFS** - логи будут доступны как локальная папка

```bash
# SSHFS пример (Linux/Mac)
mkdir -p logs_server
sshfs user@server:~/realty-system/logs logs_server
```

