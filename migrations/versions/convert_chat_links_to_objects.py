"""
Convert chat_links from array of strings to array of objects

Revision ID: convert_chat_links
Revises: chat_group_is_public
Create Date: 2026-02-17 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import json

# revision identifiers, used by Alembic.
revision = 'convert_chat_links'
down_revision = 'chat_group_is_public'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Конвертирует chat_links из формата массива строк в формат массива объектов.
    Старый формат: ["https://t.me/+...", "https://t.me/username"]
    Новый формат: [{"link": "https://t.me/+...", "telegram_chat_id": null, "title": null}, ...]
    """
    # Получаем connection для выполнения SQL
    conn = op.get_bind()
    
    # Получаем все записи из chat_groups
    result = conn.execute(text("SELECT group_id, chat_links FROM chat_groups WHERE chat_links IS NOT NULL"))
    
    for row in result:
        group_id = row[0]
        chat_links_raw = row[1]
        
        # Если chat_links пустые - пропускаем
        if not chat_links_raw:
            continue
        
        # Парсим JSON (PostgreSQL хранит JSON как строку или уже как объект)
        try:
            if isinstance(chat_links_raw, str):
                chat_links = json.loads(chat_links_raw)
            else:
                chat_links = chat_links_raw
        except (json.JSONDecodeError, TypeError):
            # Если не JSON - пропускаем
            continue
        
        # Если chat_links уже в новом формате (массив объектов) - пропускаем
        if not isinstance(chat_links, list) or len(chat_links) == 0:
            continue
        
        # Проверяем формат: если первый элемент - строка, значит старый формат
        if isinstance(chat_links[0], str):
            # Старый формат - конвертируем
            new_format = [
                {"link": link, "telegram_chat_id": None, "title": None}
                for link in chat_links
            ]
            # Обновляем в БД (PostgreSQL JSONB колонка принимает JSON строку)
            conn.execute(
                text("UPDATE chat_groups SET chat_links = :links::jsonb WHERE group_id = :group_id"),
                {"links": json.dumps(new_format), "group_id": group_id}
            )


def downgrade() -> None:
    """
    Конвертирует chat_links обратно из формата массива объектов в формат массива строк.
    Новый формат: [{"link": "https://t.me/+...", "telegram_chat_id": null, "title": null}, ...]
    Старый формат: ["https://t.me/+...", "https://t.me/username"]
    """
    # Получаем connection для выполнения SQL
    conn = op.get_bind()
    
    # Получаем все записи из chat_groups
    result = conn.execute(text("SELECT group_id, chat_links FROM chat_groups WHERE chat_links IS NOT NULL"))
    
    for row in result:
        group_id = row[0]
        chat_links_raw = row[1]
        
        if not chat_links_raw:
            continue
        
        # Парсим JSON
        try:
            if isinstance(chat_links_raw, str):
                chat_links = json.loads(chat_links_raw)
            else:
                chat_links = chat_links_raw
        except (json.JSONDecodeError, TypeError):
            continue
        
        # Проверяем формат: если первый элемент - объект, значит новый формат
        if isinstance(chat_links, list) and len(chat_links) > 0:
            if isinstance(chat_links[0], dict):
                # Новый формат - конвертируем обратно
                old_format = [item.get('link', '') for item in chat_links if item.get('link')]
                # Обновляем в БД
                conn.execute(
                    text("UPDATE chat_groups SET chat_links = :links::jsonb WHERE group_id = :group_id"),
                    {"links": json.dumps(old_format), "group_id": group_id}
                )

