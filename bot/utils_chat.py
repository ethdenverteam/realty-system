"""
Chat utilities - сохранение чатов в базу данных
"""
import logging
from datetime import datetime
from telegram import Update
from bot.database import get_db
from bot.models import Chat

logger = logging.getLogger(__name__)


def save_chat_from_update(update: Update):
    """Сохранить чат из обновления в базу данных"""
    chat = None
    chat_id = None
    chat_type = None
    
    # Handle different update types
    if update.message:
        chat = update.message.chat
    elif update.callback_query and update.callback_query.message:
        chat = update.callback_query.message.chat
    elif update.edited_message:
        chat = update.edited_message.chat
    elif update.channel_post:
        chat = update.channel_post.chat
    elif update.edited_channel_post:
        chat = update.edited_channel_post.chat
    elif update.my_chat_member:
        chat = update.my_chat_member.chat
    elif update.chat_member:
        chat = update.chat_member.chat
    
    if not chat:
        return
    
    chat_id = str(chat.id)
    chat_type = chat.type
    
    # Get title based on chat type
    if chat_type in ['group', 'supergroup', 'channel']:
        title = chat.title or f'Chat {chat_id}'
    else:
        # Private chat
        first_name = chat.first_name or ''
        last_name = chat.last_name or ''
        title = f"{first_name} {last_name}".strip() or chat.username or f'User {chat_id}'
    
    username = chat.username or ''
    
    # Save to database
    db = get_db()
    try:
        existing_chat = db.query(Chat).filter_by(
            telegram_chat_id=chat_id,
            owner_type='bot'
        ).first()
        
        if existing_chat:
            # Update existing chat
            existing_chat.title = title
            existing_chat.type = chat_type
            if username:
                if not existing_chat.filters_json:
                    existing_chat.filters_json = {}
                existing_chat.filters_json['username'] = username
        else:
            # Create new chat
            filters_data = {}
            if username:
                filters_data['username'] = username
            
            new_chat = Chat(
                telegram_chat_id=chat_id,
                title=title,
                type=chat_type,
                owner_type='bot',
                is_active=False,  # Not active by default, needs to be configured
                filters_json=filters_data if filters_data else None,
                added_date=datetime.utcnow()
            )
            db.add(new_chat)
        
        db.commit()
    except Exception as e:
        logger.error(f"Error saving chat to database: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

