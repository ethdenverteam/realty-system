"""
Admin bot chats CRUD routes
Логика: создание, обновление, удаление чатов бота
"""
from flask import Blueprint, request, jsonify, render_template
from app.database import db
from app.models.user import User
from app.models.object import Object
from app.models.chat import Chat
from app.models.telegram_account_chat import TelegramAccountChat
from app.models.chat_group import ChatGroup
from app.models.action_log import ActionLog
from app.utils.decorators import jwt_required, role_required
from app.utils.logger import log_action, log_error
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import logging

admin_bot_chats_crud_bp = Blueprint('admin_bot_chats_crud', __name__)
logger = logging.getLogger(__name__)


@admin_bot_chats_crud_bp.route('/dashboard/bot-chats/<int:chat_id>/publish-object', methods=['POST'])
@jwt_required
@role_required('admin')
def admin_publish_object_to_chat(chat_id, current_user):
    """Publish an object to a specific chat"""
    from app.models.chat import Chat
    from app.models.object import Object
    from bot.config import BOT_TOKEN
    from bot.utils import format_publication_text
    import requests
    from datetime import datetime
    
    try:
        data = request.get_json()
        object_id = data.get('object_id')
        
        if not object_id:
            return jsonify({'error': 'object_id is required'}), 400
        
        # Get chat
        chat = Chat.query.filter_by(chat_id=chat_id, owner_type='bot').first()
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        if not chat.is_active:
            return jsonify({'error': 'Chat is not active'}), 400
        
        # Get object
        obj = Object.query.filter_by(object_id=object_id).first()
        if not obj:
            return jsonify({'error': 'Object not found'}), 404
        
        # Check if object was published to this chat within last 24 hours
        # Проверка не применяется для админов (они могут публиковать без ограничений)
        # Админы уже проверены через @role_required('admin'), поэтому пропускаем проверку
        
        if not BOT_TOKEN:
            return jsonify({'error': 'BOT_TOKEN is not configured'}), 500
        
        # Получаем формат публикации из конфигурации автопубликации
        publication_format = 'default'
        from app.models.autopublish_config import AutopublishConfig
        autopublish_cfg = AutopublishConfig.query.filter_by(
            object_id=object_id
        ).first()
        if autopublish_cfg and autopublish_cfg.accounts_config_json:
            accounts_cfg = autopublish_cfg.accounts_config_json
            if isinstance(accounts_cfg, dict):
                publication_format = accounts_cfg.get('publication_format', 'default')
        
        # Format publication text
        user = obj.user
        publication_text = format_publication_text(obj, user, is_preview=False, publication_format=publication_format)
        
        # Send message via Telegram API - всегда отправляем фото если оно есть
        photos_json = obj.photos_json or []
        
        if photos_json and len(photos_json) > 0:
            # Берем первое фото (только одно фото разрешено)
            photo_data = photos_json[0]
            
            # Извлекаем путь к файлу - всегда используем путь к файлу на сервере
            photo_path = None
            if isinstance(photo_data, dict):
                # Если это объект - берем path
                photo_path = photo_data.get('path', '')
            elif isinstance(photo_data, str):
                # Если это строка - это путь к файлу
                photo_path = photo_data
            
            # Загружаем файл с сервера и отправляем
            if photo_path:
                import os
                from app.config import Config
                
                # Используем Config.UPLOAD_FOLDER напрямую
                # photo_path может быть "uploads/filename.jpg" или просто "filename.jpg"
                if photo_path.startswith('uploads/'):
                    # Убираем префикс "uploads/" и используем Config.UPLOAD_FOLDER
                    filename = photo_path.replace('uploads/', '', 1)
                    full_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                elif photo_path.startswith('/'):
                    # Абсолютный путь
                    full_path = photo_path
                else:
                    # Относительный путь - используем Config.UPLOAD_FOLDER
                    full_path = os.path.join(Config.UPLOAD_FOLDER, photo_path)
                
                if os.path.exists(full_path):
                    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto'
                    with open(full_path, 'rb') as photo_file:
                        files = {'photo': photo_file}
                        payload = {
                            'chat_id': chat.telegram_chat_id,
                            'caption': publication_text,
                            'parse_mode': 'HTML'
                        }
                        response = requests.post(url, files=files, data=payload, timeout=30)
                else:
                    logger.warning(f"Photo file not found: {full_path}, sending text only")
                    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
                    payload = {
                        'chat_id': chat.telegram_chat_id,
                        'text': publication_text,
                        'parse_mode': 'HTML'
                    }
                    response = requests.post(url, json=payload, timeout=10)
            else:
                # Если путь не найден - отправляем только текст
                url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
                payload = {
                    'chat_id': chat.telegram_chat_id,
                    'text': publication_text,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, json=payload, timeout=10)
        else:
            # Если фото нет - отправляем только текст
            url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
            payload = {
                'chat_id': chat.telegram_chat_id,
                'text': publication_text,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if not result.get('ok'):
            error_description = result.get('description', 'Unknown error')
            return jsonify({
                'error': f'Failed to send message: {error_description}',
                'details': 'Check that the bot is added to the chat and has permission to send messages'
            }), 500
        
        message_id = result.get('result', {}).get('message_id')
        
        # Update chat statistics
        chat.total_publications = (chat.total_publications or 0) + 1
        chat.last_publication = datetime.utcnow()
        
        # Create publication history entry
        from app.models.publication_history import PublicationHistory
        history = PublicationHistory(
            object_id=object_id,
            chat_id=chat_id,
            account_id=None,  # Admin publication
            published_at=datetime.utcnow(),
            message_id=str(message_id) if message_id else None,
            deleted=False
        )
        db.session.add(history)
        db.session.commit()
        
        # Update object status if needed
        if obj.status != 'опубликовано':
            obj.status = 'опубликовано'
            obj.publication_date = datetime.utcnow()
            db.session.commit()
        
        # Log action
        try:
            log_action(
                action='admin_publish_object',
                user_id=current_user.user_id,
                details={
                    'chat_id': chat_id,
                    'telegram_chat_id': chat.telegram_chat_id,
                    'object_id': object_id,
                    'message_id': message_id
                }
            )
        except Exception as log_error:
            logger.warning(f"Failed to log publish: {log_error}")
        
        return jsonify({
            'success': True,
            'message': 'Object published successfully',
            'message_id': message_id
        }), 200
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error publishing object: {e}", exc_info=True)
        return jsonify({
            'error': f'Request error: {str(e)}',
            'details': 'Check your internet connection and bot token'
        }), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in publish object: {e}", exc_info=True)
        log_error(e, 'admin_publish_object_failed', current_user.user_id, {'chat_id': chat_id, 'object_id': object_id})
        return jsonify({'error': str(e)}), 500


