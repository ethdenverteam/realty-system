"""
Chats routes
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.chat import Chat
from app.utils.decorators import jwt_required, role_required
from app.utils.logger import log_action, log_error
from datetime import datetime
import logging
import re

chats_bp = Blueprint('chats', __name__)
logger = logging.getLogger(__name__)


@chats_bp.route('/', methods=['GET'])
@jwt_required
def list_chats(current_user):
    """Get list of chats"""
    owner_type = request.args.get('owner_type', None)
    query = Chat.query.filter_by(is_active=True)
    
    if owner_type:
        query = query.filter_by(owner_type=owner_type)
    
    chats = query.all()
    return jsonify([chat.to_dict() for chat in chats])


@chats_bp.route('/bot', methods=['GET'])
@jwt_required
@role_required('admin')
def list_bot_chats(current_user):
    """Get list of bot chats (admin only)"""
    chats = Chat.query.filter_by(owner_type='bot', is_active=True).all()
    return jsonify([chat.to_dict() for chat in chats])


@chats_bp.route('/bot', methods=['POST'])
@jwt_required
@role_required('admin')
def add_bot_chat(current_user):
    """Add bot chat by Telegram link (admin only)"""
    data = request.get_json()
    chat_link = data.get('chat_link', '').strip()
    category = data.get('category', '')
    
    if not chat_link:
        return jsonify({'error': 'chat_link is required'}), 400
    
    try:
        # Extract username from link (e.g., https://t.me/CultEvnt -> CultEvnt)
        # Support formats: https://t.me/username, t.me/username, @username, username
        username = None
        if chat_link.startswith('https://t.me/') or chat_link.startswith('http://t.me/'):
            username = chat_link.split('/')[-1].replace('@', '')
        elif chat_link.startswith('t.me/'):
            username = chat_link.split('/')[-1].replace('@', '')
        elif chat_link.startswith('@'):
            username = chat_link[1:]
        else:
            username = chat_link.replace('@', '')
        
        if not username:
            return jsonify({'error': 'Invalid chat link format'}), 400
        
        # Get bot instance to resolve chat
        try:
            from bot.config import BOT_TOKEN
            from telegram import Bot
            
            bot = Bot(token=BOT_TOKEN)
            
            # Try to get chat by username
            chat_info = bot.get_chat(chat_id=f"@{username}")
            telegram_chat_id = str(chat_info.id)
            title = chat_info.title or username
            chat_type = chat_info.type
        except Exception as e:
            logger.error(f"Error getting chat info: {e}")
            return jsonify({'error': f'Cannot access chat: {str(e)}'}), 400
        
        # Check if chat already exists
        existing = Chat.query.filter_by(telegram_chat_id=telegram_chat_id).first()
        if existing:
            return jsonify({'error': 'Chat already exists'}), 400
        
        # Create chat
        chat = Chat(
            telegram_chat_id=telegram_chat_id,
            title=title,
            type=chat_type,
            category=category,
            owner_type='bot',
            is_active=True,
            added_date=datetime.utcnow()
        )
        
        db.session.add(chat)
        db.session.commit()
        
        # Log action
        log_action(
            action='admin_chat_added',
            user_id=current_user.user_id,
            details={
                'chat_id': chat.chat_id,
                'telegram_chat_id': telegram_chat_id,
                'title': title,
                'category': category
            }
        )
        
        return jsonify(chat.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        log_error(e, 'admin_chat_add_failed', current_user.user_id, {'chat_link': chat_link})
        return jsonify({'error': str(e)}), 500


@chats_bp.route('/<int:chat_id>', methods=['PUT'])
@jwt_required
def update_chat(chat_id, current_user):
    """Update chat settings"""
    chat = Chat.query.get(chat_id)
    
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404
    
    # Check permissions
    if chat.owner_type == 'bot' and current_user.web_role != 'admin':
        return jsonify({'error': 'Only admin can modify bot chats'}), 403
    
    if chat.owner_type == 'user' and chat.owner_account_id:
        from app.models.telegram_account import TelegramAccount
        account = TelegramAccount.query.get(chat.owner_account_id)
        if account and account.owner_id != current_user.user_id:
            return jsonify({'error': 'You can only modify your own chats'}), 403
    
    data = request.get_json()
    
    if 'category' in data:
        chat.category = data['category']
    if 'is_active' in data:
        chat.is_active = bool(data['is_active'])
    
    db.session.commit()
    
    # Log action
    log_action(
        action='chat_updated',
        user_id=current_user.user_id,
        details={'chat_id': chat_id, 'updates': data}
    )
    
    return jsonify(chat.to_dict())


@chats_bp.route('/<int:chat_id>', methods=['DELETE'])
@jwt_required
@role_required('admin')
def delete_chat(chat_id, current_user):
    """Delete chat (admin only)"""
    chat = Chat.query.get(chat_id)
    
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404
    
    db.session.delete(chat)
    db.session.commit()
    
    # Log action
    log_action(
        action='admin_chat_deleted',
        user_id=current_user.user_id,
        details={'chat_id': chat_id}
    )
    
    return jsonify({'message': 'Chat deleted'})

