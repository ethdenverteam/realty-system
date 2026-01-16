"""
Admin routes - реорганизованные админские роуты
"""
from flask import Blueprint, request, jsonify, render_template
from app.database import db
from app.models.user import User
from app.models.object import Object
from app.models.chat import Chat
from app.models.action_log import ActionLog
from app.utils.decorators import jwt_required, role_required
from app.utils.logger import log_action, log_error
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import logging

admin_routes_bp = Blueprint('admin_routes', __name__)
logger = logging.getLogger(__name__)


@admin_routes_bp.route('/dashboard', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_dashboard(current_user):
    """Admin dashboard page"""
    return render_template('admin/dashboard.html', user=current_user)


@admin_routes_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_stats(current_user):
    """Get admin statistics"""
    from app.models.telegram_account import TelegramAccount
    from app.models.publication_queue import PublicationQueue
    
    # Total users
    users_count = User.query.count()
    
    # Total objects
    objects_count = Object.query.count()
    
    # Publications today
    today = datetime.utcnow().date()
    publications_today = PublicationQueue.query.filter(
        func.date(PublicationQueue.created_at) == today
    ).count()
    
    # Active accounts
    accounts_count = TelegramAccount.query.filter_by(is_active=True).count()
    
    return jsonify({
        'users_count': users_count,
        'objects_count': objects_count,
        'publications_today': publications_today,
        'accounts_count': accounts_count
    })


@admin_routes_bp.route('/dashboard/users', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_users(current_user):
    """Get list of all users"""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])


@admin_routes_bp.route('/dashboard/users/<int:user_id>/role', methods=['PUT'])
@jwt_required
@role_required('admin')
def update_user_role(user_id, current_user):
    """Update user role"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    old_web_role = user.web_role
    old_bot_role = user.bot_role
    
    if 'web_role' in data:
        user.web_role = data['web_role']
    if 'bot_role' in data:
        user.bot_role = data['bot_role']
    
    try:
        db.session.commit()
        
        log_action(
            action='admin_role_changed',
            user_id=current_user.user_id,
            details={
                'target_user_id': user_id,
                'target_username': user.username,
                'old_web_role': old_web_role,
                'new_web_role': user.web_role if 'web_role' in data else None,
                'old_bot_role': old_bot_role,
                'new_bot_role': user.bot_role if 'bot_role' in data else None
            }
        )
        
        return jsonify(user.to_dict())
    except Exception as e:
        db.session.rollback()
        log_error(e, 'admin_role_change_failed', current_user.user_id, {'target_user_id': user_id})
        return jsonify({'error': str(e)}), 500


@admin_routes_bp.route('/dashboard/logs', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_logs_page(current_user):
    """Logs viewer page"""
    return render_template('admin/logs.html', user=current_user)


@admin_routes_bp.route('/dashboard/logs/data', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_logs_data(current_user):
    """Get logs data"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    action = request.args.get('action')
    user_id = request.args.get('user_id', type=int)
    
    query = ActionLog.query
    
    if action:
        query = query.filter(ActionLog.action == action)
    if user_id:
        query = query.filter(ActionLog.user_id == user_id)
    
    query = query.order_by(desc(ActionLog.created_at))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'logs': [log.to_dict() for log in pagination.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    })


@admin_routes_bp.route('/dashboard/bot-chats', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_bot_chats_page(current_user):
    """Bot chats management page"""
    return render_template('admin/bot_chats.html', user=current_user)


@admin_routes_bp.route('/dashboard/bot-chats/list', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_bot_chats_list(current_user):
    """Get list of bot chats"""
    chats = Chat.query.filter_by(owner_type='bot', is_active=True).all()
    return jsonify([chat.to_dict() for chat in chats])


@admin_routes_bp.route('/dashboard/bot-chats', methods=['POST'])
@jwt_required
@role_required('admin')
def admin_add_bot_chat(current_user):
    """Add bot chat"""
    data = request.get_json()
    chat_link = data.get('chat_link', '').strip()
    filters = data.get('filters', {})
    
    if not chat_link:
        return jsonify({'error': 'chat_link is required'}), 400
    
    try:
        # Extract username from link
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
        from bot.config import BOT_TOKEN
        from telegram import Bot
        
        bot = Bot(token=BOT_TOKEN)
        chat_info = bot.get_chat(chat_id=f"@{username}")
        telegram_chat_id = str(chat_info.id)
        title = chat_info.title or username
        chat_type = chat_info.type
        
        # Check if chat already exists
        existing = Chat.query.filter_by(telegram_chat_id=telegram_chat_id).first()
        if existing:
            return jsonify({'error': 'Chat already exists'}), 400
        
        # Create chat
        chat = Chat(
            telegram_chat_id=telegram_chat_id,
            title=title,
            type=chat_type,
            category=None,  # Legacy, use filters_json instead
            filters_json=filters,
            owner_type='bot',
            is_active=True,
            added_date=datetime.utcnow()
        )
        
        db.session.add(chat)
        db.session.commit()
        
        log_action(
            action='admin_chat_added',
            user_id=current_user.user_id,
            details={
                'chat_id': chat.chat_id,
                'telegram_chat_id': telegram_chat_id,
                'title': title,
                'filters': filters
            }
        )
        
        return jsonify(chat.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding chat: {e}", exc_info=True)
        log_error(e, 'admin_chat_add_failed', current_user.user_id, {'chat_link': chat_link})
        return jsonify({'error': str(e)}), 500


@admin_routes_bp.route('/dashboard/bot-chats/<int:chat_id>', methods=['PUT'])
@jwt_required
@role_required('admin')
def admin_update_bot_chat(chat_id, current_user):
    """Update bot chat filters"""
    chat = Chat.query.filter_by(chat_id=chat_id, owner_type='bot').first()
    
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404
    
    data = request.get_json()
    
    if 'filters_json' in data:
        chat.filters_json = data['filters_json']
    if 'is_active' in data:
        chat.is_active = bool(data['is_active'])
    
    try:
        db.session.commit()
        
        log_action(
            action='admin_chat_updated',
            user_id=current_user.user_id,
            details={
                'chat_id': chat_id,
                'updates': data
            }
        )
        
        return jsonify(chat.to_dict())
    except Exception as e:
        db.session.rollback()
        log_error(e, 'admin_chat_update_failed', current_user.user_id, {'chat_id': chat_id})
        return jsonify({'error': str(e)}), 500


@admin_routes_bp.route('/dashboard/bot-chats/<int:chat_id>', methods=['DELETE'])
@jwt_required
@role_required('admin')
def admin_delete_bot_chat(chat_id, current_user):
    """Delete bot chat"""
    chat = Chat.query.filter_by(chat_id=chat_id, owner_type='bot').first()
    
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404
    
    try:
        db.session.delete(chat)
        db.session.commit()
        
        log_action(
            action='admin_chat_deleted',
            user_id=current_user.user_id,
            details={'chat_id': chat_id}
        )
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        log_error(e, 'admin_chat_delete_failed', current_user.user_id, {'chat_id': chat_id})
        return jsonify({'error': str(e)}), 500


@admin_routes_bp.route('/dashboard/bot-chats/config', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_bot_chats_config(current_user):
    """Get configuration for chat filters (districts, rooms types, price ranges)"""
    from app.models.system_setting import SystemSetting
    
    # Get districts config
    districts_setting = SystemSetting.query.filter_by(key='districts_config').first()
    districts_config = districts_setting.value_json if districts_setting else {}
    
    # Rooms types
    rooms_types = ['Студия', '1к', '2к', '3к', '4+к', 'Дом', 'евро1к', 'евро2к', 'евро3к']
    
    # Price ranges (default)
    price_ranges = [
        {'min': 0, 'max': 3000, 'label': 'До 3000'},
        {'min': 3000, 'max': 4000, 'label': '3000-4000'},
        {'min': 4000, 'max': 6000, 'label': '4000-6000'},
        {'min': 6000, 'max': 8000, 'label': '6000-8000'},
        {'min': 8000, 'max': 10000, 'label': '8000-10000'},
        {'min': 10000, 'max': 999999, 'label': 'От 10000'},
    ]
    
    return jsonify({
        'districts': districts_config,
        'rooms_types': rooms_types,
        'price_ranges': price_ranges
    })

