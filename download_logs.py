#!/usr/bin/env python3
"""
Скрипт для скачивания логов с сервера напрямую в папку logs_server/
Использование: python download_logs.py [API_URL] [API_TOKEN]
"""

import os
import sys
import requests
from pathlib import Path

# Конфигурация
DEFAULT_API_URL = "http://localhost"  # Или ваш домен, например "https://your-domain.com"
LOCAL_LOGS_DIR = Path(__file__).parent / "logs_server"

# Типы логов для скачивания
LOG_TYPES = ['app', 'errors', 'bot', 'bot_errors']
LOG_FILENAMES = {
    'app': 'app.log',
    'errors': 'errors.log',
    'bot': 'bot.log',
    'bot_errors': 'bot_errors.log'
}


def get_api_token():
    """Получить API токен из переменной окружения или запросить у пользователя"""
    token = os.getenv('REALTY_API_TOKEN')
    if not token and len(sys.argv) > 2:
        token = sys.argv[2]
    if not token:
        # Пытаемся прочитать из файла (если есть)
        token_file = Path(__file__).parent / '.api_token'
        if token_file.exists():
            token = token_file.read_text().strip()
        else:
            print("⚠️  API токен не найден!")
            print("   Способы указать токен:")
            print("   1. Передать как аргумент: python download_logs.py <API_URL> <TOKEN>")
            print("   2. Создать файл .api_token с токеном")
            print("   3. Установить переменную окружения REALTY_API_TOKEN")
            print()
            token = input("Введите API токен (или Enter чтобы выйти): ").strip()
            if not token:
                sys.exit(1)
    return token


def get_api_url():
    """Получить API URL"""
    if len(sys.argv) > 1:
        return sys.argv[1].rstrip('/')
    return os.getenv('REALTY_API_URL', DEFAULT_API_URL)


def download_log_file(api_url, token, log_type, output_dir):
    """Скачать конкретный файл лога"""
    url = f"{api_url}/api/logs/file/{log_type}"
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        filename = LOG_FILENAMES[log_type]
        output_path = output_dir / filename
        
        # Скачать файл
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = output_path.stat().st_size / 1024  # KB
        print(f"  ✅ {filename} ({file_size:.1f} KB)")
        return True
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"  ⚠️  {LOG_FILENAMES[log_type]} - файл не найден на сервере")
            return False
        print(f"  ❌ {LOG_FILENAMES[log_type]} - ошибка HTTP {e.response.status_code}")
        return False
    except Exception as e:
        print(f"  ❌ {LOG_FILENAMES[log_type]} - ошибка: {e}")
        return False


def main():
    """Основная функция"""
    print("🔄 Скачивание логов с сервера...")
    print()
    
    # Получить URL и токен
    api_url = get_api_url()
    token = get_api_token()
    
    print(f"Сервер: {api_url}")
    print(f"Папка: {LOCAL_LOGS_DIR}")
    print()
    
    # Создать папку если не существует
    LOCAL_LOGS_DIR.mkdir(exist_ok=True)
    
    # Скачать все логи
    success_count = 0
    for log_type in LOG_TYPES:
        print(f"Скачивание {log_type}...", end=' ')
        if download_log_file(api_url, token, log_type, LOCAL_LOGS_DIR):
            success_count += 1
        else:
            print(f"  ⚠️  {LOG_FILENAMES[log_type]} - пропущен")
    
    print()
    if success_count > 0:
        print(f"✅ Скачано файлов: {success_count}/{len(LOG_TYPES)}")
        print(f"📁 Логи находятся в: {LOCAL_LOGS_DIR}")
    else:
        print("❌ Не удалось скачать ни одного файла")
        print("   Проверьте:")
        print("   1. API URL правильный")
        print("   2. API токен действителен")
        print("   3. Сервер доступен")
        sys.exit(1)


if __name__ == "__main__":
    main()

