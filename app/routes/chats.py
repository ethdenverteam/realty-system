"""
Chats routes
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.chat import Chat
from app.models.chat_group import ChatGroup
from app.models.telegram_account import TelegramAccount
from app.utils.decorators import jwt_required, role_required
from app.utils.logger import log_action, log_error
from datetime import datetime
import logging
import re
from sqlalchemy import or_, String

chats_bp = Blueprint('chats', __name__)
logger = logging.getLogger(__name__)


@chats_bp.route('/', methods=['GET'])
@jwt_required
def list_chats(current_user):
    """Get list of chats"""
    try:
        from sqlalchemy.exc import ProgrammingError
        from sqlalchemy import inspect as sqlalchemy_inspect
        from sqlalchemy import text
        
        owner_type = request.args.get('owner_type', None)
        account_id = request.args.get('account_id', type=int)
        search = request.args.get('search', type=str)
        
        # Check if filters_json column exists
        inspector = sqlalchemy_inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('chats')]
        has_filters_json = 'filters_json' in columns
        has_cached_at = 'cached_at' in columns
        
        # If filters_json doesn't exist, use raw SQL
        if not has_filters_json:
            base_sql = """
                SELECT chat_id, telegram_chat_id, title, type, category, 
                       owner_type, owner_account_id, is_active, members_count,
                       added_date, last_publication, total_publications
                FROM chats
                WHERE is_active = true
            """
            params = {}
            if owner_type:
                base_sql += " AND owner_type = :owner_type"
                params['owner_type'] = owner_type
            if account_id:
                base_sql += " AND owner_account_id = :account_id AND owner_type = 'user'"
                params['account_id'] = account_id
            if search:
                base_sql += """
                    AND (
                        title ILIKE :q OR
                        telegram_chat_id ILIKE :q OR
                        COALESCE(category, '') ILIKE :q OR
                        owner_type ILIKE :q OR
                        CAST(members_count AS TEXT) ILIKE :q
                    )
                """
                params['q'] = f"%{search}%"
            sql = text(base_sql)
            
            result_proxy = db.session.execute(sql, params)
            rows = result_proxy.fetchall()
            
            result = []
            for row in rows:
                chat_dict = {
                    'chat_id': row[0],
                    'telegram_chat_id': row[1],
                    'title': row[2],
                    'type': row[3],
                    'category': row[4],
                    'owner_type': row[5],
                    'owner_account_id': row[6],
                    'is_active': row[7],
                    'members_count': row[8],
                    'added_date': row[9].isoformat() if row[9] else None,
                    'last_publication': row[10].isoformat() if row[10] else None,
                    'total_publications': row[11],
                    'filters_json': {},
                    'cached_at': None
                }
                result.append(chat_dict)
            return jsonify(result)
        
        # Column exists, use normal ORM query
        query = Chat.query.filter_by(is_active=True)
        if owner_type:
            query = query.filter_by(owner_type=owner_type)
        if account_id:
            # Filter by account for user chats
            from app.models.telegram_account import TelegramAccount
            account = TelegramAccount.query.get(account_id)
            if account and (current_user.web_role == 'admin' or account.owner_id == current_user.user_id):
                query = query.filter_by(owner_account_id=account_id, owner_type='user')
            else:
                return jsonify({'error': 'Access denied'}), 403

        if search:
            like_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Chat.title.ilike(like_pattern),
                    Chat.telegram_chat_id.ilike(like_pattern),
                    Chat.category.ilike(like_pattern),
                    Chat.owner_type.ilike(like_pattern),
                    # Cast members_count and filters_json to text for search
                    db.cast(Chat.members_count, String).ilike(like_pattern),
                )
            )
        
        chats = query.all()
        return jsonify([chat.to_dict() for chat in chats])
    except ProgrammingError as e:
        db.session.rollback()
        if 'filters_json' in str(e):
            logger.error(f"Database column 'filters_json' does not exist. Please run migrations: {e}", exc_info=True)
            return jsonify({
                'error': 'Database schema is outdated. The filters_json column is missing.',
                'details': 'Please run database migrations: alembic upgrade head'
            }), 500
        raise


@chats_bp.route('/bot', methods=['GET'])
@jwt_required
@role_required('admin')
def list_bot_chats(current_user):
    """Get list of bot chats (admin only)"""
    try:
        from sqlalchemy.exc import ProgrammingError
        from sqlalchemy import inspect as sqlalchemy_inspect
        from sqlalchemy import text
        
        # Check if filters_json column exists
        inspector = sqlalchemy_inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('chats')]
        has_filters_json = 'filters_json' in columns
        
        # If filters_json doesn't exist, use raw SQL
        if not has_filters_json:
            sql = text("""
                SELECT chat_id, telegram_chat_id, title, type, category, 
                       owner_type, owner_account_id, is_active, members_count,
                       added_date, last_publication, total_publications
                FROM chats
                WHERE owner_type = 'bot' AND is_active = true
            """)
            result_proxy = db.session.execute(sql)
            rows = result_proxy.fetchall()
            
            result = []
            for row in rows:
                chat_dict = {
                    'chat_id': row[0],
                    'telegram_chat_id': row[1],
                    'title': row[2],
                    'type': row[3],
                    'category': row[4],
                    'owner_type': row[5],
                    'owner_account_id': row[6],
                    'is_active': row[7],
                    'members_count': row[8],
                    'added_date': row[9].isoformat() if row[9] else None,
                    'last_publication': row[10].isoformat() if row[10] else None,
                    'total_publications': row[11],
                    'filters_json': {}
                }
                result.append(chat_dict)
            return jsonify(result)
        
        # Column exists, use normal ORM query
        chats = Chat.query.filter_by(owner_type='bot', is_active=True).all()
        return jsonify([chat.to_dict() for chat in chats])
    except ProgrammingError as e:
        db.session.rollback()
        if 'filters_json' in str(e):
            logger.error(f"Database column 'filters_json' does not exist. Please run migrations: {e}", exc_info=True)
            return jsonify({
                'error': 'Database schema is outdated. The filters_json column is missing.',
                'details': 'Please run database migrations: alembic upgrade head'
            }), 500
        raise


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
    
    data = request.get_json() or {}
    
    if 'category' in data:
        chat.category = data['category'] if data['category'] else None
    if 'filters_json' in data:
        chat.filters_json = data['filters_json'] if data['filters_json'] else None
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


@chats_bp.route('/groups', methods=['GET'])
@jwt_required
def list_chat_groups(current_user):
    """Get list of chat groups for current user"""
    try:
        groups = ChatGroup.query.filter_by(user_id=current_user.user_id).all()
        return jsonify([group.to_dict() for group in groups])
    except Exception as e:
        logger.error(f"Error listing chat groups: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@chats_bp.route('/groups', methods=['POST'])
@jwt_required
def create_chat_group(current_user):
    """Create a new chat group"""
    data = request.get_json() or {}
    name = data.get('name')
    description = data.get('description', '')
    chat_ids = data.get('chat_ids', [])
    category = data.get('category', '')
    filters_json = data.get('filters_json', {})
    
    if not name:
        return jsonify({'error': 'name is required'}), 400
    
    if not isinstance(chat_ids, list) or len(chat_ids) == 0:
        return jsonify({'error': 'chat_ids must be a non-empty list'}), 400
    
    # Проверяем, что все чаты принадлежат пользователю
    user_chats = Chat.query.filter(
        Chat.chat_id.in_(chat_ids),
        Chat.owner_type == 'user',
        Chat.owner_account_id.in_(
            db.session.query(TelegramAccount.account_id).filter_by(owner_id=current_user.user_id)
        )
    ).all()
    
    if len(user_chats) != len(chat_ids):
        return jsonify({'error': 'Some chats do not belong to user'}), 400
    
    try:
        group = ChatGroup(
            user_id=current_user.user_id,
            name=name,
            description=description,
            chat_ids=chat_ids,
            category=category if category else None,
            filters_json=filters_json if filters_json else None
        )
        db.session.add(group)
        db.session.commit()
        
        log_action(
            action='chat_group_created',
            user_id=current_user.user_id,
            details={'group_id': group.group_id, 'name': name, 'chat_count': len(chat_ids), 'category': category}
        )
        
        return jsonify({'success': True, 'group': group.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating chat group: {e}", exc_info=True)
        log_error(e, 'chat_group_creation_failed', current_user.user_id, {'name': name})
        return jsonify({'error': str(e)}), 500


@chats_bp.route('/groups/<int:group_id>', methods=['PUT'])
@jwt_required
def update_chat_group(group_id, current_user):
    """Update a chat group"""
    group = ChatGroup.query.filter_by(group_id=group_id, user_id=current_user.user_id).first()
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    data = request.get_json() or {}
    
    if 'name' in data:
        group.name = data['name']
    if 'description' in data:
        group.description = data.get('description', '')
    if 'category' in data:
        group.category = data['category'] if data['category'] else None
    if 'filters_json' in data:
        group.filters_json = data['filters_json'] if data['filters_json'] else None
    if 'chat_ids' in data:
        chat_ids = data['chat_ids']
        if not isinstance(chat_ids, list):
            return jsonify({'error': 'chat_ids must be a list'}), 400
        
        # Проверяем, что все чаты принадлежат пользователю
        user_chats = Chat.query.filter(
            Chat.chat_id.in_(chat_ids),
            Chat.owner_type == 'user',
            Chat.owner_account_id.in_(
                db.session.query(TelegramAccount.account_id).filter_by(owner_id=current_user.user_id)
            )
        ).all()
        
        if len(user_chats) != len(chat_ids):
            return jsonify({'error': 'Some chats do not belong to user'}), 400
        
        group.chat_ids = chat_ids
    
    try:
        db.session.commit()
        
        log_action(
            action='chat_group_updated',
            user_id=current_user.user_id,
            details={'group_id': group_id}
        )
        
        return jsonify({'success': True, 'group': group.to_dict()})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating chat group: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@chats_bp.route('/groups/<int:group_id>', methods=['DELETE'])
@jwt_required
def delete_chat_group(group_id, current_user):
    """Delete a chat group"""
    group = ChatGroup.query.filter_by(group_id=group_id, user_id=current_user.user_id).first()
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    try:
        db.session.delete(group)
        db.session.commit()
        
        log_action(
            action='chat_group_deleted',
            user_id=current_user.user_id,
            details={'group_id': group_id}
        )
        
        return jsonify({'success': True, 'message': 'Group deleted'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting chat group: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

