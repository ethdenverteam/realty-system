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

# Типы ТЕСТОВЫХ логов для скачивания (короткие, свежие логи для AI)
TEST_LOG_TYPES = [
    'test_app', 'test_errors', 'test_database', 'test_api', 
    'test_celery', 'test_bot', 'test_bot_errors'
]
TEST_LOG_FILENAMES = {
    'test_app': 'test_app.log',
    'test_errors': 'test_errors.log',
    'test_database': 'test_database.log',
    'test_api': 'test_api.log',
    'test_celery': 'test_celery.log',
    'test_bot': 'test_bot.log',
    'test_bot_errors': 'test_bot_errors.log'
}


def get_api_token():
    """Получить LOGS_DOWNLOAD_TOKEN из переменной окружения или файла"""
    token = os.getenv('REALTY_LOGS_DOWNLOAD_TOKEN')
    if not token and len(sys.argv) > 2:
        token = sys.argv[2]
    if not token:
        # Пытаемся прочитать из файла (если есть)
        token_file = Path(__file__).parent / '.api_token'
        if token_file.exists():
            token = token_file.read_text().strip()
        else:
            print("⚠️  LOGS_DOWNLOAD_TOKEN не найден!")
            print("   Это отдельный токен для скачивания логов (не JWT).")
            print("   Способы указать токен:")
            print("   1. Передать как аргумент: python download_logs.py <API_URL> <TOKEN>")
            print("   2. Создать файл .api_token с токеном")
            print("   3. Установить переменную окружения REALTY_LOGS_DOWNLOAD_TOKEN")
            print()
            print("   Токен настраивается на сервере в переменной окружения LOGS_DOWNLOAD_TOKEN")
            print()
            token = input("Введите LOGS_DOWNLOAD_TOKEN (или Enter чтобы выйти): ").strip()
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
    # Use token as query parameter (LOGS_DOWNLOAD_TOKEN)
    params = {'token': token}
    
    try:
        response = requests.get(url, params=params, stream=True, timeout=30)
        response.raise_for_status()
        
        filename = TEST_LOG_FILENAMES[log_type]
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
            print(f"  ⚠️  {TEST_LOG_FILENAMES[log_type]} - файл не найден на сервере")
            return False
        elif e.response.status_code == 401:
            print(f"  ❌ {TEST_LOG_FILENAMES[log_type]} - неверный токен")
            return False
        print(f"  ❌ {TEST_LOG_FILENAMES[log_type]} - ошибка HTTP {e.response.status_code}")
        return False
    except Exception as e:
        print(f"  ❌ {TEST_LOG_FILENAMES[log_type]} - ошибка: {e}")
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
    
    # Скачать все ТЕСТОВЫЕ логи (короткие, свежие)
    print("📥 Скачивание тестовых логов (свежие логи с последнего деплоя)...")
    print()
    success_count = 0
    for log_type in TEST_LOG_TYPES:
        print(f"Скачивание {log_type}...", end=' ')
        if download_log_file(api_url, token, log_type, LOCAL_LOGS_DIR):
            success_count += 1
        else:
            print(f"  ⚠️  {TEST_LOG_FILENAMES[log_type]} - пропущен")
    
    print()
    if success_count > 0:
        print(f"✅ Скачано файлов: {success_count}/{len(TEST_LOG_TYPES)}")
        print(f"📁 Тестовые логи находятся в: {LOCAL_LOGS_DIR}")
        print()
        print("💡 Эти логи содержат только события с последнего деплоя")
        print("   (очищаются при каждом deploy.sh для свежего анализа)")
    else:
        print("❌ Не удалось скачать ни одного файла")
        print("   Проверьте:")
        print("   1. API URL правильный")
        print("   2. LOGS_DOWNLOAD_TOKEN действителен (настроен на сервере)")
        print("   3. Сервер доступен")
        print("   4. deploy.sh был запущен (логи могли быть очищены)")
        sys.exit(1)


if __name__ == "__main__":
    main()

