"""
Скрипт для обновления районов из HTML файла
Извлекает районы из районы.html и обновляет districts_config в SystemSetting
"""
import sys
import os
import re
import json
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app
from app.database import db
from app.models.system_setting import SystemSetting

def extract_districts_from_html(html_file_path: str) -> dict:
    """
    Извлекает районы из HTML файла
    Возвращает словарь {название_района: название_района}
    """
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Ищем все элементы <li> с data-name
    pattern = r'<li[^>]*data-name="([^"]+)"[^>]*>'
    matches = re.findall(pattern, html_content)
    
    districts = {}
    for district_name in matches:
        # Очищаем название от лишних символов
        district_name = district_name.strip()
        if district_name:
            # Используем название как ключ и значение
            districts[district_name] = district_name
    
    return districts

def update_districts_in_db(districts: dict):
    """
    Обновляет districts_config в SystemSetting
    Удаляет старые районы и добавляет новые
    """
    with app.app_context():
        # Получаем или создаем настройку
        districts_setting = SystemSetting.query.filter_by(key='districts_config').first()
        
        if districts_setting:
            # Обновляем существующую настройку
            districts_setting.value_json = districts
            print(f"Обновлено {len(districts)} районов в существующей настройке")
        else:
            # Создаем новую настройку
            districts_setting = SystemSetting(
                key='districts_config',
                value_json=districts,
                description='Configuration for districts (updated from HTML)'
            )
            db.session.add(districts_setting)
            print(f"Создана новая настройка с {len(districts)} районами")
        
        db.session.commit()
        print(f"Успешно сохранено {len(districts)} районов в БД")
        
        # Выводим список районов
        print("\nСписок районов:")
        for i, (name, value) in enumerate(sorted(districts.items()), 1):
            print(f"{i:3d}. {name}")

def main():
    """Основная функция"""
    # Путь к HTML файлу
    html_file = project_root / 'районы.html'
    
    if not html_file.exists():
        print(f"Ошибка: файл {html_file} не найден")
        return 1
    
    print(f"Чтение районов из {html_file}...")
    districts = extract_districts_from_html(str(html_file))
    
    if not districts:
        print("Ошибка: не найдено ни одного района в HTML файле")
        return 1
    
    print(f"Найдено {len(districts)} районов")
    print("\nОбновление БД...")
    update_districts_in_db(districts)
    
    print("\nГотово!")
    return 0

if __name__ == '__main__':
    sys.exit(main())

