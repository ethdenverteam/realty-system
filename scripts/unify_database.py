"""
Скрипт для унификации использования БД
Заменяет все использования bot.database на app.database
"""
import re
import os
from pathlib import Path

# Файлы для обработки
BOT_FILES = [
    'bot/handlers_object.py',
    'bot/handlers_object_edit.py',
    'bot/handlers_objects_view.py',
    'bot/handlers_publication.py',
    'bot/handlers_settings.py',
    'bot/utils_chat.py',
    'bot/utils_logger.py',
    'workers/tasks.py',
    'app/routes/objects.py',
    'app/routes/user_routes.py',
    'app/routes/admin_routes.py',
]

def replace_in_file(file_path: str):
    """Заменяет использования bot.database на app.database в файле"""
    full_path = Path(__file__).parent.parent / file_path
    if not full_path.exists():
        print(f"Файл не найден: {file_path}")
        return False
    
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Замены импортов
    content = re.sub(
        r'from bot\.database import get_db',
        'from app.database import db',
        content
    )
    content = re.sub(
        r'from bot\.database import get_db as get_bot_db',
        'from app.database import db',
        content
    )
    
    # Замены использования get_db()
    # Паттерн: db = get_db() ... try: ... finally: db.close()
    content = re.sub(
        r'db\s*=\s*get_db\(\)\s*\n\s*try:\s*\n(.*?)\s*finally:\s*\n\s*db\.close\(\)',
        r'db.session\1',
        content,
        flags=re.DOTALL
    )
    
    # Простые замены: db = get_db() -> удалить, db.query -> db.session.query
    content = re.sub(
        r'(\s+)db\s*=\s*get_db\(\)\s*\n\s*try:\s*\n',
        r'\1',
        content
    )
    content = re.sub(
        r'\s+finally:\s*\n\s+db\.close\(\)',
        '',
        content
    )
    
    # Замены методов
    content = re.sub(r'\bdb\.query\(', 'db.session.query(', content)
    content = re.sub(r'\bdb\.add\(', 'db.session.add(', content)
    content = re.sub(r'\bdb\.commit\(', 'db.session.commit(', content)
    content = re.sub(r'\bdb\.rollback\(', 'db.session.rollback(', content)
    content = re.sub(r'\bdb\.delete\(', 'db.session.delete(', content)
    content = re.sub(r'\bdb\.close\(', '', content)  # Удаляем close(), т.к. db.session не нужно закрывать
    
    # Замены для db_session
    content = re.sub(
        r'db_session\s*=\s*get_db\(\)',
        '',
        content
    )
    content = re.sub(
        r'db_session\.query\(',
        'db.session.query(',
        content
    )
    content = re.sub(
        r'db_session\.add\(',
        'db.session.add(',
        content
    )
    content = re.sub(
        r'db_session\.commit\(',
        'db.session.commit(',
        content
    )
    content = re.sub(
        r'db_session\.delete\(',
        'db.session.delete(',
        content
    )
    content = re.sub(
        r'db_session\.close\(\)',
        '',
        content
    )
    
    if content != original_content:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Обновлен: {file_path}")
        return True
    else:
        print(f"  Без изменений: {file_path}")
        return False

def main():
    """Основная функция"""
    print("Унификация использования БД...")
    print("=" * 50)
    
    updated_count = 0
    for file_path in BOT_FILES:
        if replace_in_file(file_path):
            updated_count += 1
    
    print("=" * 50)
    print(f"Обновлено файлов: {updated_count}/{len(BOT_FILES)}")
    print("\n⚠️  ВНИМАНИЕ: Проверьте изменения вручную!")
    print("   Некоторые замены могут требовать дополнительной правки.")

if __name__ == '__main__':
    main()

