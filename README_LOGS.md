# Логирование бота

## Просмотр логов в реальном времени

### Через docker-compose (рекомендуется)
```bash
cd ~/realty-system
docker-compose logs -f bot
```

### Через docker напрямую
```bash
docker logs -f realty_bot
```

### Просмотр последних 100 строк
```bash
docker-compose logs --tail=100 bot
```

## Файлы логов

Логи бота сохраняются в директории `logs/`:
- `bot.log` - все логи (DEBUG и выше)
- `bot_errors.log` - только ошибки (ERROR и выше)

## Настройка

Логи настраиваются в `bot/main.py`:
- Консольный вывод: INFO уровень, формат `[timestamp] | LEVEL | name | message`
- Файловый вывод: DEBUG уровень, детальный формат с номером строки

## Решение проблем

Если логи не обновляются в реальном времени:
1. Убедитесь, что используете `-f` флаг: `docker-compose logs -f bot`
2. Проверьте, что `PYTHONUNBUFFERED=1` установлен в docker-compose.yml
3. Перезапустите бота: `docker-compose restart bot`

