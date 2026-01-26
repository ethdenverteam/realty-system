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


@admin_routes_bp.route('/dashboard/users/add-admin-by-telegram-id', methods=['POST'])
@jwt_required
@role_required('admin')
def add_admin_by_telegram_id(current_user):
    """Add admin role to user by telegram_id"""
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    
    if not telegram_id:
        return jsonify({'error': 'telegram_id is required'}), 400
    
    try:
        telegram_id_int = int(telegram_id) if isinstance(telegram_id, str) else int(telegram_id)
        user = User.query.filter_by(telegram_id=telegram_id_int).first()
        
        if not user:
            # Create new user with admin role
            user = User(
                telegram_id=telegram_id_int,
                web_role='admin',
                bot_role='premium'
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"Created new user with telegram_id {telegram_id_int} and admin role")
            
            log_action(
                action='admin_user_created',
                user_id=current_user.user_id,
                details={
                    'target_telegram_id': telegram_id_int,
                    'web_role': 'admin',
                    'bot_role': 'premium'
                }
            )
        else:
            old_role = user.web_role
            user.web_role = 'admin'
            db.session.commit()
            logger.info(f"Updated user {user.user_id} (telegram_id: {telegram_id_int}) role from '{old_role}' to 'admin'")
            
            log_action(
                action='admin_role_changed',
                user_id=current_user.user_id,
                details={
                    'target_user_id': user.user_id,
                    'target_telegram_id': telegram_id_int,
                    'target_username': user.username,
                    'old_web_role': old_role,
                    'new_web_role': 'admin'
                }
            )
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'message': f'User {telegram_id_int} is now admin'
        })
    except ValueError:
        return jsonify({'error': f'Invalid telegram_id: {telegram_id}. Must be a number.'}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding admin: {e}", exc_info=True)
        log_error(e, 'add_admin_failed', current_user.user_id, {'telegram_id': telegram_id})
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
    try:
        from sqlalchemy.exc import ProgrammingError
        from sqlalchemy import inspect as sqlalchemy_inspect
        from sqlalchemy import text
        
        # Check if filters_json column exists before querying
        inspector = sqlalchemy_inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('chats')]
        has_filters_json = 'filters_json' in columns
        
        # If filters_json column doesn't exist, use raw SQL to avoid SQLAlchemy trying to load it
        if not has_filters_json:
            logger.warning("filters_json column missing, using raw SQL query")
            # Use raw SQL to query without filters_json column
            sql = text("""
                SELECT chat_id, telegram_chat_id, title, type, category, 
                       owner_type, owner_account_id, is_active, members_count,
                       added_date, last_publication, total_publications
                FROM chats
                WHERE owner_type = :owner_type AND is_active = true
            """)
            result_proxy = db.session.execute(sql, {'owner_type': 'bot'})
            rows = result_proxy.fetchall()
            
            # Convert rows to dict
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
                    'filters_json': {}  # Default empty dict since column doesn't exist
                }
                result.append(chat_dict)
            
            logger.info(f"Returned {len(result)} chats using raw SQL query (filters_json column missing)")
            return jsonify(result)
        
        # Column exists, use normal ORM query
        # But still use raw SQL to be safe (filters_json might not be committed yet)
        try:
            # Use raw SQL even if column exists to avoid issues
            # Try to include filters_json if column exists
            sql = text("""
                SELECT chat_id, telegram_chat_id, title, type, category, 
                       owner_type, owner_account_id, is_active, members_count,
                       added_date, last_publication, total_publications,
                       COALESCE(filters_json, '{}'::jsonb) as filters_json
                FROM chats
                WHERE owner_type = :owner_type AND is_active = true
            """)
            result_proxy = db.session.execute(sql, {'owner_type': 'bot'})
            rows = result_proxy.fetchall()
            
            result = []
            for row in rows:
                # Parse filters_json if it's a string, otherwise use as-is
                filters_json = row[12] if len(row) > 12 else {}
                if isinstance(filters_json, str):
                    try:
                        import json
                        filters_json = json.loads(filters_json)
                    except:
                        filters_json = {}
                elif filters_json is None:
                    filters_json = {}
                else:
                    # If it's already a dict (from JSONB), use it directly
                    if not isinstance(filters_json, dict):
                        try:
                            import json
                            filters_json = json.loads(str(filters_json))
                        except:
                            filters_json = {}
                
                logger.debug(f"Chat {row[0]} ({row[2]}): filters_json = {filters_json}, type = {type(filters_json)}")
                
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
                    'filters_json': filters_json
                }
                result.append(chat_dict)
            
            logger.info(f"Returned {len(result)} chats using raw SQL query")
            return jsonify(result)
        except ProgrammingError as query_error:
            # If query still fails, try using raw SQL without filters_json
            if 'filters_json' in str(query_error):
                logger.warning(f"filters_json column missing despite check, using alternative query: {query_error}")
                # IMPORTANT: Rollback failed transaction before executing new query
                db.session.rollback()
                # Use raw SQL to query without filters_json column
                sql = text("""
                    SELECT chat_id, telegram_chat_id, title, type, category, 
                           owner_type, owner_account_id, is_active, members_count,
                           added_date, last_publication, total_publications
                    FROM chats
                    WHERE owner_type = :owner_type AND is_active = true
                """)
                result_proxy = db.session.execute(sql, {'owner_type': 'bot'})
                rows = result_proxy.fetchall()
                
                # Convert rows to dict
                result = []
                for row in rows:
                    # Try to get filters_json from database using ORM
                    chat_id = row[0]
                    try:
                        chat_orm = Chat.query.filter_by(chat_id=chat_id).first()
                        filters_json = chat_orm.filters_json if chat_orm and hasattr(chat_orm, 'filters_json') else {}
                    except:
                        filters_json = {}
                    
                    # If filters_json is empty, try to parse category
                    if not filters_json and row[4]:  # category
                        category = row[4]
                        filters_json = {}
                        if category.startswith('rooms_'):
                            filters_json['rooms_types'] = [category.replace('rooms_', '')]
                        elif category.startswith('district_'):
                            filters_json['districts'] = [category.replace('district_', '')]
                        elif category.startswith('price_'):
                            parts = category.replace('price_', '').split('_')
                            if len(parts) == 2:
                                filters_json['price_min'] = float(parts[0])
                                filters_json['price_max'] = float(parts[1])
                    
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
                        'filters_json': filters_json
                    }
                    result.append(chat_dict)
                
                logger.info(f"Returned {len(result)} chats using fallback query with parsed category")
                return jsonify(result)
            raise
        
        # Convert to dict, handling missing filters_json column
        result = []
        for chat in chats:
            chat_dict = {
                'chat_id': chat.chat_id,
                'telegram_chat_id': chat.telegram_chat_id,
                'title': chat.title,
                'type': chat.type,
                'category': chat.category,
                'owner_type': chat.owner_type,
                'owner_account_id': chat.owner_account_id,
                'is_active': chat.is_active,
                'members_count': chat.members_count,
                'added_date': chat.added_date.isoformat() if chat.added_date else None,
                'last_publication': chat.last_publication.isoformat() if chat.last_publication else None,
                'total_publications': chat.total_publications,
            }
            # Only add filters_json if column exists and we can access it
            if has_filters_json:
                try:
                    chat_dict['filters_json'] = chat.filters_json or {}
                except AttributeError:
                    chat_dict['filters_json'] = {}
            else:
                chat_dict['filters_json'] = {}
            result.append(chat_dict)
        
        return jsonify(result)
    except ProgrammingError as e:
        # Rollback failed transaction
        db.session.rollback()
        if 'filters_json' in str(e):
            logger.error(f"Database column 'filters_json' does not exist. Please run migrations: {e}", exc_info=True)
            return jsonify({
                'error': 'Database schema is outdated. The filters_json column is missing.',
                'details': 'Please run database migrations: alembic upgrade head'
            }), 500
        raise
    except Exception as e:
        # Rollback failed transaction
        db.session.rollback()
        logger.error(f"Error getting bot chats list: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


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
        # Extract username or chat_id from link
        username = None
        chat_id_direct = None
        
        # Check if it's a direct chat ID (numeric)
        if chat_link.lstrip('-').isdigit():
            chat_id_direct = chat_link
        elif chat_link.startswith('https://t.me/') or chat_link.startswith('http://t.me/'):
            username = chat_link.split('/')[-1].replace('@', '')
        elif chat_link.startswith('t.me/'):
            username = chat_link.split('/')[-1].replace('@', '')
        elif chat_link.startswith('@'):
            username = chat_link[1:]
        else:
            username = chat_link.replace('@', '')
        
        if not username and not chat_id_direct:
            return jsonify({'error': 'Invalid chat link format'}), 400
        
        # Get bot instance to resolve chat
        from bot.config import BOT_TOKEN
        from telegram import Bot
        import asyncio
        
        async def get_chat_info():
            bot = Bot(token=BOT_TOKEN)
            try:
                if chat_id_direct:
                    # Direct chat ID
                    chat_info = await bot.get_chat(chat_id=int(chat_id_direct))
                else:
                    # Try with @username first
                    try:
                        chat_info = await bot.get_chat(chat_id=f"@{username}")
                    except Exception:
                        # If that fails, try with chat_id if it's numeric
                        if username.isdigit() or (username.startswith('-') and username[1:].isdigit()):
                            chat_info = await bot.get_chat(chat_id=int(username))
                        else:
                            raise
            except Exception as e:
                logger.error(f"Error getting chat info: {e}")
                raise
            return chat_info
        
        chat_info = asyncio.run(get_chat_info())
        telegram_chat_id = str(chat_info.id)
        title = chat_info.title or (chat_info.first_name or '') + ' ' + (chat_info.last_name or '') or username or f'Chat {telegram_chat_id}'
        chat_type = chat_info.type
        
        # Check if chat already exists (using raw SQL to avoid filters_json issue)
        from sqlalchemy import text
        try:
            sql = text("""
                SELECT chat_id, telegram_chat_id, title, type, category, 
                       owner_type, owner_account_id, is_active, members_count,
                       added_date, last_publication, total_publications
                FROM chats
                WHERE telegram_chat_id = :telegram_chat_id
                LIMIT 1
            """)
            result_proxy = db.session.execute(sql, {'telegram_chat_id': telegram_chat_id})
            existing_row = result_proxy.fetchone()
            if existing_row:
                return jsonify({'error': 'Chat already exists'}), 400
        except Exception as check_error:
            logger.warning(f"Error checking existing chat: {check_error}")
            # Continue anyway - might be filters_json issue
        
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
    # Use raw SQL to check existence first
    from sqlalchemy import text
    try:
        sql = text("""
            SELECT chat_id FROM chats
            WHERE chat_id = :chat_id AND owner_type = :owner_type
            LIMIT 1
        """)
        result_proxy = db.session.execute(sql, {'chat_id': chat_id, 'owner_type': 'bot'})
        if not result_proxy.fetchone():
            return jsonify({'error': 'Chat not found'}), 404
        
        # Use ORM for update (filters_json might exist after migration)
        chat = Chat.query.filter_by(chat_id=chat_id, owner_type='bot').first()
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
    except Exception as e:
        logger.error(f"Error getting chat for update: {e}", exc_info=True)
        # Fallback
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
    # Use raw SQL to delete (avoids filters_json issue)
    from sqlalchemy import text
    try:
        # Check if chat exists
        sql = text("""
            SELECT chat_id FROM chats
            WHERE chat_id = :chat_id AND owner_type = :owner_type
            LIMIT 1
        """)
        result_proxy = db.session.execute(sql, {'chat_id': chat_id, 'owner_type': 'bot'})
        if not result_proxy.fetchone():
            return jsonify({'error': 'Chat not found'}), 404
        
        # Delete using raw SQL
        delete_sql = text("""
            DELETE FROM chats
            WHERE chat_id = :chat_id AND owner_type = :owner_type
        """)
        db.session.execute(delete_sql, {'chat_id': chat_id, 'owner_type': 'bot'})
    except Exception as e:
        logger.error(f"Error deleting chat: {e}", exc_info=True)
        # Fallback to ORM
        chat = Chat.query.filter_by(chat_id=chat_id, owner_type='bot').first()
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        db.session.delete(chat)
    
    try:
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


@admin_routes_bp.route('/dashboard/bot-chats/get-by-id', methods=['POST'])
@jwt_required
@role_required('admin')
def admin_get_chat_by_id(current_user):
    """Get chat information by chat ID using getChat API
    
    This method uses getChat which doesn't conflict with bot polling.
    You can provide chat ID directly (e.g., -1002632748579) or username.
    """
    try:
        from bot.config import BOT_TOKEN
        from telegram import Bot
        import asyncio
        
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN is not configured")
            return jsonify({'error': 'BOT_TOKEN is not configured'}), 500
        
        data = request.get_json()
        chat_id_input = data.get('chat_id', '').strip()
        
        if not chat_id_input:
            return jsonify({'error': 'chat_id is required'}), 400
        
        async def get_chat_info():
            bot = Bot(token=BOT_TOKEN)
            try:
                # Try as integer first (for group/channel IDs like -1002632748579)
                if chat_id_input.lstrip('-').isdigit():
                    chat_info = await bot.get_chat(chat_id=int(chat_id_input))
                # Try as username (with or without @)
                elif chat_id_input.startswith('@'):
                    chat_info = await bot.get_chat(chat_id=chat_id_input)
                else:
                    # Try with @ prefix
                    chat_info = await bot.get_chat(chat_id=f"@{chat_id_input}")
            except Exception as e:
                logger.error(f"Error getting chat info for {chat_id_input}: {e}")
                raise
            return chat_info
        
        chat_info = asyncio.run(get_chat_info())
        
        # Format response
        chat_data = {
            'id': str(chat_info.id),
            'title': chat_info.title or (chat_info.first_name or '') + ' ' + (chat_info.last_name or '') or chat_info.username or f'Chat {chat_info.id}',
            'type': chat_info.type,
            'username': chat_info.username or '',
            'description': getattr(chat_info, 'description', '') or '',
            'members_count': getattr(chat_info, 'members_count', 0) or 0
        }
        
        logger.info(f"Retrieved chat info: {chat_data['id']} ({chat_data['title']})")
        
        return jsonify({
            'chat': chat_data,
            'message': 'Chat retrieved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error getting chat by ID: {e}", exc_info=True)
        log_error(e, 'admin_get_chat_by_id_failed', current_user.user_id, {'chat_id': chat_id_input})
        
        error_msg = str(e)
        if 'chat not found' in error_msg.lower() or 'not found' in error_msg.lower():
            return jsonify({
                'error': 'Chat not found',
                'details': f'The chat with ID "{chat_id_input}" was not found. Make sure the bot is a member of the chat or the chat ID is correct.'
            }), 404
        
        return jsonify({
            'error': str(e),
            'details': 'Check server logs for details'
        }), 500


@admin_routes_bp.route('/dashboard/bot-chats/fetch', methods=['POST'])
@jwt_required
@role_required('admin')
def admin_fetch_bot_chats(current_user):
    """Fetch all chats from Telegram bot using getUpdates
    
    This will automatically stop the bot, fetch chats, then restart it.
    For getting a specific chat, use /dashboard/bot-chats/get-by-id instead.
    """
    import subprocess
    import time
    import os
    
    bot_stopped = False
    bot_container_name = os.getenv('BOT_CONTAINER_NAME', 'realty_bot')
    
    try:
        from bot.config import BOT_TOKEN
        import requests
        
        # Check if we should stop the bot
        data = request.get_json() or {}
        stop_bot = data.get('stop_bot', True)  # Default to True
        
        if stop_bot:
            # Try to stop the bot container
            try:
                logger.info(f"Stopping bot container: {bot_container_name}")
                result = subprocess.run(
                    ['docker', 'stop', bot_container_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    bot_stopped = True
                    logger.info("Bot stopped successfully, waiting 2 seconds...")
                    time.sleep(2)  # Wait for bot to fully stop
                else:
                    logger.warning(f"Failed to stop bot: {result.stderr}")
                    # Continue anyway - might not be running
            except FileNotFoundError:
                logger.warning("Docker command not found - cannot stop bot automatically")
            except Exception as stop_error:
                logger.warning(f"Error stopping bot: {stop_error}")
                # Continue anyway
        
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN is not configured")
            return jsonify({'error': 'BOT_TOKEN is not configured'}), 500
        
        # First, try to get updates with offset=-1 to check for conflicts
        # This will fail immediately if bot is running
        test_url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates'
        test_params = {'offset': -1, 'timeout': 1, 'limit': 1}
        
        try:
            test_response = requests.get(test_url, params=test_params, timeout=5)
            test_data = test_response.json()
            
            # Check for conflict in test request
            if not test_data.get('ok'):
                error_description = test_data.get('description', 'Unknown error')
                error_code = test_data.get('error_code', 0)
                
                if error_code == 409 or 'Conflict' in error_description or 'getUpdates' in error_description or 'terminated by other' in error_description:
                    logger.warning(f"Bot conflict detected during test: {error_description}")
                    return jsonify({
                        'error': 'Bot conflict: Another bot instance is running',
                        'details': 'The bot is currently running and using getUpdates. To fetch chats, you need to temporarily stop the bot container, fetch chats, then restart it.',
                        'conflict': True,
                        'suggestion': 'Run: docker-compose stop bot (then fetch chats, then: docker-compose start bot)'
                    }), 409
        except Exception as test_error:
            # If test fails, continue anyway - might be network issue
            logger.debug(f"Test request failed (non-critical): {test_error}")
        
        chats_dict = {}
        
        # Get bot info to get bot user ID
        bot_info_url = f'https://api.telegram.org/bot{BOT_TOKEN}/getMe'
        bot_user_id = None
        try:
            bot_info_response = requests.get(bot_info_url, timeout=5)
            bot_info_data = bot_info_response.json()
            if bot_info_data.get('ok'):
                bot_user_id = bot_info_data['result'].get('id')
                logger.info(f"Bot user ID: {bot_user_id}")
        except Exception as e:
            logger.warning(f"Could not get bot info: {e}")
        
        # Get updates using Telegram API - get ALL updates from history
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates'
        offset = 0
        max_iterations = 100  # Increased to get more history
        processed_updates = 0
        
        logger.info(f"Starting to fetch chats, BOT_TOKEN length: {len(BOT_TOKEN)}")
        
        for iteration in range(max_iterations):
            params = {'offset': offset, 'timeout': 1, 'limit': 100}
            try:
                logger.debug(f"Fetching updates, iteration {iteration + 1}, offset: {offset}")
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if not data.get('ok'):
                    error_description = data.get('description', 'Unknown error')
                    error_code = data.get('error_code', 0)
                    
                    # Handle conflict error (409) - bot is already running
                    if error_code == 409 or 'Conflict' in error_description or 'getUpdates' in error_description or 'terminated by other' in error_description:
                        logger.warning(f"Bot conflict detected: {error_description}")
                        return jsonify({
                            'error': 'Bot conflict: Another bot instance is running',
                            'details': 'The bot is currently running and using getUpdates. To fetch chats, you need to temporarily stop the bot container, fetch chats, then restart it.',
                            'conflict': True,
                            'suggestion': 'Run: docker-compose stop bot (then fetch chats, then: docker-compose start bot)'
                        }), 409
                    
                    logger.error(f"Telegram API error: {error_description}")
                    return jsonify({
                        'error': f'Telegram API error: {error_description}',
                        'details': 'Check that the bot is running and the token is correct'
                    }), 500
                
            except requests.exceptions.RequestException as e:
                error_str = str(e)
                # Check if it's a conflict error in the exception message
                if 'Conflict' in error_str or 'getUpdates' in error_str or '409' in error_str:
                    logger.warning(f"Bot conflict detected in request exception: {error_str}")
                    return jsonify({
                        'error': 'Bot conflict: Another bot instance is running',
                        'details': 'The bot is currently running and using getUpdates. To fetch chats, you need to temporarily stop the bot or use chats that are already in the database.',
                        'conflict': True,
                        'suggestion': 'Stop the bot container temporarily, fetch chats, then restart the bot'
                    }), 409
                logger.error(f"Request error fetching updates: {e}", exc_info=True)
                return jsonify({
                    'error': f'Request error to Telegram API: {str(e)}',
                    'details': 'Check your internet connection and bot token'
                }), 500
            except Exception as e:
                logger.error(f"Unexpected error fetching updates: {e}", exc_info=True)
                return jsonify({
                    'error': f'Unexpected error: {str(e)}'
                }), 500
            
            if not data.get('result'):
                logger.info("No more updates to process")
                break
            
            updates = data['result']
            if not updates:
                logger.info("No updates in this batch")
                break
            
            logger.info(f"Processing {len(updates)} updates (total processed: {processed_updates})")
            
            for update in updates:
                chat = None
                chat_id = None
                chat_type = None
                
                # Handle different update types
                if 'message' in update:
                    chat = update['message'].get('chat', {})
                elif 'callback_query' in update:
                    chat = update['callback_query'].get('message', {}).get('chat', {})
                elif 'edited_message' in update:
                    chat = update['edited_message'].get('chat', {})
                elif 'channel_post' in update:
                    chat = update['channel_post'].get('chat', {})
                elif 'edited_channel_post' in update:
                    chat = update['edited_channel_post'].get('chat', {})
                elif 'my_chat_member' in update:
                    chat = update['my_chat_member'].get('chat', {})
                elif 'chat_member' in update:
                    chat = update['chat_member'].get('chat', {})
                
                if chat:
                    chat_id = str(chat.get('id'))
                    chat_type = chat.get('type')
                    
                    # Get title based on chat type
                    if chat_type in ['group', 'supergroup', 'channel']:
                        title = chat.get('title', '')
                    else:
                        first_name = chat.get('first_name', '')
                        last_name = chat.get('last_name', '')
                        title = f"{first_name} {last_name}".strip() or chat.get('username', '') or f'User {chat_id}'
                    
                    username = chat.get('username', '')
                    
                    if chat_id and chat_id not in chats_dict:
                        chats_dict[chat_id] = {
                            'id': chat_id,
                            'title': title or f'Chat {chat_id}',
                            'type': chat_type,
                            'username': username,
                            'is_admin': None  # Will be checked later for groups
                        }
                        logger.debug(f"Added chat: {chat_id} ({title})")
                
                offset = max(offset, update.get('update_id', 0) + 1)
                processed_updates += 1
            
            if len(updates) < 100:  # Last batch
                logger.info("Last batch of updates processed")
                break
        
        logger.info(f"Total updates processed: {processed_updates}, unique chats found: {len(chats_dict)}")
        
        # For groups/supergroups/channels, check if bot is admin or can read messages
        # This is important to filter only chats where bot can actually see messages
        groups_to_check = [c for c in chats_dict.values() if c['type'] in ['group', 'supergroup', 'channel']]
        logger.info(f"Checking admin status for {len(groups_to_check)} groups/supergroups/channels")
        
        get_chat_member_url = f'https://api.telegram.org/bot{BOT_TOKEN}/getChatMember'
        checked_count = 0
        for chat_data in groups_to_check:
            try:
                # Check bot's member status in the chat
                params = {'chat_id': chat_data['id'], 'user_id': bot_user_id if bot_user_id else BOT_TOKEN.split(':')[0]}
                response = requests.get(get_chat_member_url, params=params, timeout=5)
                if response.status_code == 200:
                    member_data = response.json()
                    if member_data.get('ok'):
                        status = member_data['result'].get('status', '')
                        # Bot can see messages if it's admin, creator, or member (for groups)
                        # For channels, bot needs to be admin or member
                        can_see_messages = status in ['administrator', 'creator', 'member']
                        if chat_data['type'] == 'channel':
                            # For channels, bot needs to be admin to post
                            can_see_messages = status in ['administrator', 'creator']
                        chat_data['is_admin'] = status in ['administrator', 'creator']
                        chat_data['can_see_messages'] = can_see_messages
                        
                        if not can_see_messages:
                            logger.debug(f"Bot cannot see messages in chat {chat_data['id']} ({chat_data['title']}), status: {status}")
                    else:
                        # If we can't get member info, assume bot can't see messages
                        chat_data['can_see_messages'] = False
                        logger.debug(f"Cannot get member info for chat {chat_data['id']}: {member_data.get('description', 'Unknown')}")
                else:
                    chat_data['can_see_messages'] = False
                    logger.debug(f"Error checking chat {chat_data['id']}: HTTP {response.status_code}")
                
                checked_count += 1
                # Rate limiting: sleep every 20 requests
                if checked_count % 20 == 0:
                    import time
                    time.sleep(1)
            except Exception as e:
                logger.warning(f"Error checking admin status for chat {chat_data['id']}: {e}")
                chat_data['can_see_messages'] = False
        
        # Filter chats: keep private chats (bot received messages) and groups where bot can see messages
        filtered_chats = []
        for chat_id, chat_data in chats_dict.items():
            if chat_data['type'] == 'private':
                # All private chats where bot received messages are included
                filtered_chats.append(chat_data)
            elif chat_data['type'] in ['group', 'supergroup', 'channel']:
                # Only include groups where bot can see messages
                if chat_data.get('can_see_messages', False):
                    filtered_chats.append(chat_data)
                else:
                    logger.debug(f"Excluding chat {chat_id} ({chat_data['title']}) - bot cannot see messages")
        
        chats = filtered_chats
        logger.info(f"After filtering: {len(chats)} chats where bot can see messages (from {len(chats_dict)} total)")
        
        # Convert to list
        chats = list(chats_dict.values())
        logger.info(f"Total chats found: {len(chats)}")
        
        # Save found chats to database (if any found)
        if len(chats) > 0:
            try:
                saved_count = 0
                updated_count = 0
                for chat_data in chats:
                    chat_id_str = str(chat_data['id'])
                    existing_chat = Chat.query.filter_by(telegram_chat_id=chat_id_str, owner_type='bot').first()
                    
                    if existing_chat:
                        # Update existing chat
                        existing_chat.title = chat_data.get('title', existing_chat.title)
                        existing_chat.type = chat_data.get('type', existing_chat.type)
                        if chat_data.get('username'):
                            # Store username in filters_json (we'll use it as metadata storage)
                            if not existing_chat.filters_json:
                                existing_chat.filters_json = {}
                            existing_chat.filters_json['username'] = chat_data['username']
                        updated_count += 1
                    else:
                        # Create new chat
                        filters_data = {}
                        if chat_data.get('username'):
                            filters_data['username'] = chat_data['username']
                        
                        new_chat = Chat(
                            telegram_chat_id=chat_id_str,
                            title=chat_data.get('title', f'Chat {chat_id_str}'),
                            type=chat_data.get('type', 'private'),
                            owner_type='bot',
                            is_active=False,  # Not active by default, needs to be configured
                            filters_json=filters_data if filters_data else None
                        )
                        db.session.add(new_chat)
                        saved_count += 1
                
                db.session.commit()
                logger.info(f"Saved {saved_count} new chats, updated {updated_count} existing chats in database")
            except Exception as save_error:
                logger.error(f"Error saving chats to database: {save_error}", exc_info=True)
                db.session.rollback()
        
        # If no chats found from getUpdates, try to get from database
        if len(chats) == 0:
            logger.warning("No chats found from getUpdates - trying to get from database")
            try:
                db_chats = Chat.query.filter_by(owner_type='bot').all()
                if db_chats:
                    logger.info(f"Found {len(db_chats)} chats in database")
                    chats = []
                    for db_chat in db_chats:
                        username = ''
                        if db_chat.filters_json and isinstance(db_chat.filters_json, dict):
                            username = db_chat.filters_json.get('username', '')
                        
                        chats.append({
                            'id': db_chat.telegram_chat_id,
                            'title': db_chat.title,
                            'type': db_chat.type,
                            'username': username
                        })
                else:
                    logger.warning("No chats found in database either")
            except Exception as db_error:
                logger.warning(f"Error getting chats from database: {db_error}")
        
        # Separate groups and users
        groups = [c for c in chats if c['type'] in ['group', 'supergroup', 'channel']]
        users = [c for c in chats if c['type'] == 'private']
        
        logger.info(f"Groups: {len(groups)}, Users: {len(users)}, Total: {len(chats)}")
        
        return jsonify({
            'groups': groups,
            'users': users,
            'all': chats
        })
        
    except Exception as e:
        logger.error(f"Error fetching chats: {e}", exc_info=True)
        log_error(e, 'admin_fetch_chats_failed', current_user.user_id, {})
        
        # Check if it's a conflict error
        if 'Conflict' in str(e) or 'getUpdates' in str(e):
            return jsonify({
                'error': 'Bot conflict: Another bot instance is running',
                'details': 'The bot is currently running and using getUpdates. To fetch chats, you need to temporarily stop the bot.',
                'conflict': True
            }), 409
        
        return jsonify({
            'error': str(e),
            'details': 'Check server logs for details'
        }), 500
    finally:
        # Always try to restart the bot if we stopped it
        if 'bot_stopped' in locals() and bot_stopped:
            try:
                logger.info(f"Restarting bot container: {bot_container_name}")
                result = subprocess.run(
                    ['docker', 'start', bot_container_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info("Bot restarted successfully")
                else:
                    logger.error(f"Failed to restart bot: {result.stderr}")
            except Exception as restart_error:
                logger.error(f"Error restarting bot: {restart_error}")


@admin_routes_bp.route('/dashboard/bot-chats/districts', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_get_districts(current_user):
    """Get all districts"""
    from app.models.system_setting import SystemSetting
    
    districts_setting = SystemSetting.query.filter_by(key='districts_config').first()
    districts_config = districts_setting.value_json if districts_setting else {}
    
    return jsonify({
        'districts': districts_config
    })


@admin_routes_bp.route('/dashboard/bot-chats/districts', methods=['POST'])
@jwt_required
@role_required('admin')
def admin_add_district(current_user):
    """Add a new district"""
    from app.models.system_setting import SystemSetting
    
    data = request.get_json()
    district_name = data.get('name', '').strip()
    
    if not district_name:
        return jsonify({'error': 'District name is required'}), 400
    
    try:
        districts_setting = SystemSetting.query.filter_by(key='districts_config').first()
        
        if districts_setting:
            # Ensure we have a dict, not None
            districts_config = districts_setting.value_json if districts_setting.value_json is not None else {}
            if not isinstance(districts_config, dict):
                logger.warning(f"districts_config is not a dict, converting. Type: {type(districts_config)}, Value: {districts_config}")
                districts_config = {}
        else:
            districts_config = {}
            districts_setting = SystemSetting(
                key='districts_config',
                value_json={},
                description='Configuration for districts'
            )
            db.session.add(districts_setting)
            db.session.flush()  # Flush to get the ID
        
        if district_name in districts_config:
            return jsonify({'error': 'District already exists'}), 400
        
        # Add district to config
        districts_config[district_name] = district_name
        
        # Update the setting - make sure we're working with a fresh dict
        districts_setting.value_json = dict(districts_config)  # Create new dict to ensure it's saved
        districts_setting.updated_by = current_user.user_id
        
        # Commit the changes
        try:
            db.session.commit()
        except Exception as commit_error:
            db.session.rollback()
            logger.error(f"Error committing district: {commit_error}", exc_info=True)
            return jsonify({'error': f'Failed to save district: {str(commit_error)}'}), 500
        
        # Verify by re-querying (don't use refresh/expire for JSON fields)
        db.session.expire_all()  # Expire all to force reload
        districts_setting_verify = SystemSetting.query.filter_by(key='districts_config').first()
        
        if not districts_setting_verify:
            logger.error("districts_setting was deleted after commit!")
            return jsonify({'error': 'Failed to save district - setting not found after commit'}), 500
        
        saved_config = districts_setting_verify.value_json if districts_setting_verify.value_json is not None else {}
        
        # Ensure it's a dict
        if not isinstance(saved_config, dict):
            logger.error(f"Saved config is not a dict! Type: {type(saved_config)}, Value: {saved_config}")
            saved_config = {}
        
        logger.info(f"District '{district_name}' added. Total districts: {len(saved_config)}")
        
        if district_name not in saved_config:
            logger.error(f"District '{district_name}' was not saved correctly! Saved config keys: {list(saved_config.keys()) if isinstance(saved_config, dict) else 'not a dict'}")
            # Try one more time with direct SQL update
            try:
                from sqlalchemy import text
                import json
                # Get current value and merge with new district
                current_config = districts_setting_verify.value_json or {}
                if not isinstance(current_config, dict):
                    current_config = {}
                current_config[district_name] = district_name
                # Update using JSON string
                update_sql = text("""
                    UPDATE system_settings 
                    SET value_json = CAST(:new_config AS jsonb)
                    WHERE key = 'districts_config'
                """)
                new_config_json = json.dumps(current_config)
                db.session.execute(update_sql, {'new_config': new_config_json})
                db.session.commit()
                
                # Verify again
                districts_setting_verify = SystemSetting.query.filter_by(key='districts_config').first()
                saved_config = districts_setting_verify.value_json if districts_setting_verify else {}
                if district_name not in saved_config:
                    return jsonify({'error': 'Failed to save district - database update failed'}), 500
            except Exception as sql_error:
                logger.error(f"SQL update fallback failed: {sql_error}", exc_info=True)
                return jsonify({'error': f'Failed to save district: {str(sql_error)}'}), 500
        
        # Log action (don't fail if logging fails)
        try:
            log_action(
                action='admin_district_added',
                user_id=current_user.user_id,
                details={'district_name': district_name}
            )
        except Exception as log_error:
            logger.warning(f"Failed to log district addition: {log_error}")
        
        return jsonify({
            'districts': saved_config,
            'message': f'District "{district_name}" added successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding district: {e}", exc_info=True)
        log_error(e, 'admin_district_add_failed', current_user.user_id, {'district_name': district_name})
        return jsonify({'error': str(e)}), 500


@admin_routes_bp.route('/dashboard/bot-chats/districts/<district_name>', methods=['DELETE'])
@jwt_required
@role_required('admin')
def admin_delete_district(district_name, current_user):
    """Delete a district"""
    from app.models.system_setting import SystemSetting
    
    try:
        districts_setting = SystemSetting.query.filter_by(key='districts_config').first()
        
        if not districts_setting or not districts_setting.value_json:
            return jsonify({'error': 'No districts found'}), 404
        
        districts_config = districts_setting.value_json
        
        if district_name not in districts_config:
            return jsonify({'error': 'District not found'}), 404
        
        del districts_config[district_name]
        districts_setting.value_json = districts_config
        districts_setting.updated_by = current_user.user_id
        
        db.session.commit()
        
        # Log action (don't fail if logging fails)
        try:
            log_action(
                action='admin_district_deleted',
                user_id=current_user.user_id,
                details={'district_name': district_name}
            )
        except Exception as log_error:
            logger.warning(f"Failed to log district deletion: {log_error}")
        
        return jsonify({
            'districts': districts_config
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting district: {e}", exc_info=True)
        log_error(e, 'admin_district_delete_failed', current_user.user_id, {'district_name': district_name})
        return jsonify({'error': str(e)}), 500


@admin_routes_bp.route('/dashboard/bot-chats/<int:chat_id>/test-publish', methods=['POST'])
@jwt_required
@role_required('admin')
def admin_test_publish_to_chat(chat_id, current_user):
    """Test publish a message to a chat"""
    from app.models.chat import Chat
    from bot.config import BOT_TOKEN
    import requests
    
    try:
        # Get chat
        chat = Chat.query.filter_by(chat_id=chat_id, owner_type='bot').first()
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        if not chat.is_active:
            return jsonify({'error': 'Chat is not active'}), 400
        
        if not BOT_TOKEN:
            return jsonify({'error': 'BOT_TOKEN is not configured'}), 500
        
        # Create test message with binding information
        test_message = "🧪 <b>Тестовая публикация</b>\n\nЭто тестовое сообщение для проверки работы публикации в чат.\n\n"
        
        # Add binding information
        filters = chat.filters_json or {}
        binding_parts = []
        
        if filters.get('rooms_types') and len(filters['rooms_types']) > 0:
            binding_parts.append(f"Комнаты: {', '.join(filters['rooms_types'])}")
        
        if filters.get('districts') and len(filters['districts']) > 0:
            binding_parts.append(f"Районы: {', '.join(filters['districts'])}")
        
        if filters.get('price_min') or filters.get('price_max'):
            price_min = filters.get('price_min', 0)
            price_max = filters.get('price_max', '∞')
            binding_parts.append(f"Цена: {price_min} - {price_max} тыс. руб.")
        
        # Legacy category support
        if not binding_parts and chat.category:
            if chat.category.startswith('rooms_'):
                room_type = chat.category.replace('rooms_', '')
                binding_parts.append(f"Комнаты: {room_type}")
            elif chat.category.startswith('district_'):
                district = chat.category.replace('district_', '')
                binding_parts.append(f"Район: {district}")
            elif chat.category.startswith('price_'):
                parts = chat.category.replace('price_', '').split('_')
                if len(parts) == 2:
                    binding_parts.append(f"Цена: {parts[0]} - {parts[1]} тыс. руб.")
        
        if binding_parts:
            test_message += "<b>Привязка чата:</b>\n"
            for part in binding_parts:
                test_message += f"• {part}\n"
        else:
            test_message += "<b>Привязка чата:</b> не указана\n"
        
        # Send message via Telegram API
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
        payload = {
            'chat_id': chat.telegram_chat_id,
            'text': test_message,
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
        
        # Log action
        try:
            log_action(
                action='admin_test_publish',
                user_id=current_user.user_id,
                details={'chat_id': chat_id, 'telegram_chat_id': chat.telegram_chat_id}
            )
        except Exception as log_error:
            logger.warning(f"Failed to log test publish: {log_error}")
        
        return jsonify({
            'success': True,
            'message': 'Test message sent successfully',
            'message_id': result.get('result', {}).get('message_id')
        }), 200
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending test message: {e}", exc_info=True)
        return jsonify({
            'error': f'Request error: {str(e)}',
            'details': 'Check your internet connection and bot token'
        }), 500
    except Exception as e:
        logger.error(f"Error in test publish: {e}", exc_info=True)
        log_error(e, 'admin_test_publish_failed', current_user.user_id, {'chat_id': chat_id})
        return jsonify({'error': str(e)}), 500


@admin_routes_bp.route('/dashboard/bot-chats/<int:chat_id>/publish-object', methods=['POST'])
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
        from app.models.publication_history import PublicationHistory
        from datetime import timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_publication = PublicationHistory.query.filter(
            PublicationHistory.object_id == object_id,
            PublicationHistory.chat_id == chat_id,
            PublicationHistory.published_at >= yesterday,
            PublicationHistory.deleted == False
        ).first()
        
        if recent_publication:
            return jsonify({
                'error': 'Object was already published to this chat within 24 hours',
                'last_publication': recent_publication.published_at.isoformat()
            }), 400
        
        if not BOT_TOKEN:
            return jsonify({'error': 'BOT_TOKEN is not configured'}), 500
        
        # Format publication text
        user = obj.user
        publication_text = format_publication_text(obj, user, is_preview=False)
        
        # Send message via Telegram API
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
        payload = {
            'chat_id': chat.telegram_chat_id,
            'text': publication_text,
            'parse_mode': 'HTML'
        }
        
        # If object has photos, send with media
        photos_json = obj.photos_json or []
        if photos_json and len(photos_json) > 0:
            # For now, send text only. Media support can be added later
            # TODO: Implement media sending
            pass
        
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

