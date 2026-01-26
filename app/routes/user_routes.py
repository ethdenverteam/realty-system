"""
User routes - реорганизованные пользовательские роуты
"""
from flask import Blueprint, request, jsonify, render_template
from app.database import db
from app.models.object import Object
from app.models.publication_queue import PublicationQueue
from app.models.publication_history import PublicationHistory
from app.models.telegram_account import TelegramAccount
from app.utils.decorators import jwt_required
from app.utils.logger import log_action, log_error
from sqlalchemy import func
from datetime import datetime
import logging

user_routes_bp = Blueprint('user_routes', __name__)
logger = logging.getLogger(__name__)


@user_routes_bp.route('/dashboard', methods=['GET'])
@jwt_required
def user_dashboard(current_user):
    """User dashboard page"""
    return render_template('user/dashboard.html', user=current_user)


@user_routes_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required
def user_stats(current_user):
    """Get user dashboard statistics"""
    # User's objects count
    objects_count = Object.query.filter_by(user_id=current_user.user_id).count()
    
    # Objects by status
    objects_by_status = db.session.query(
        Object.status,
        func.count(Object.object_id)
    ).filter_by(user_id=current_user.user_id).group_by(Object.status).all()
    
    # Today's publications
    today = datetime.utcnow().date()
    today_publications = PublicationQueue.query.filter(
        PublicationQueue.user_id == current_user.user_id,
        func.date(PublicationQueue.created_at) == today
    ).count()
    
    # Total publications
    total_publications = db.session.query(PublicationHistory).join(
        Object, PublicationHistory.object_id == Object.object_id
    ).filter(
        Object.user_id == current_user.user_id
    ).count()
    
    # Accounts count
    accounts_count = TelegramAccount.query.filter_by(
        owner_id=current_user.user_id,
        is_active=True
    ).count()
    
    return jsonify({
        'objects_count': objects_count,
        'objects_by_status': dict(objects_by_status),
        'today_publications': today_publications,
        'total_publications': total_publications,
        'accounts_count': accounts_count
    })


@user_routes_bp.route('/dashboard/objects', methods=['GET'])
@jwt_required
def user_objects_page(current_user):
    """Objects list page"""
    return render_template('user/objects.html', user=current_user)


@user_routes_bp.route('/dashboard/objects/list', methods=['GET'])
@jwt_required
def user_objects_list(current_user):
    """Get list of user's objects"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    rooms_type = request.args.get('rooms_type')
    search = request.args.get('search')
    sort_by = request.args.get('sort_by', 'creation_date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Build query
    query = Object.query.filter_by(user_id=current_user.user_id)
    
    # Apply filters
    if status:
        query = query.filter(Object.status == status)
    if rooms_type:
        query = query.filter(Object.rooms_type == rooms_type)
    if search:
        from sqlalchemy import or_
        search_filter = or_(
            Object.object_id.ilike(f'%{search}%'),
            Object.address.ilike(f'%{search}%'),
            Object.comment.ilike(f'%{search}%')
        )
        query = query.filter(search_filter)
    
    # Apply sorting
    if sort_by == 'price':
        order_by = Object.price.desc() if sort_order == 'desc' else Object.price.asc()
    elif sort_by == 'publication_date':
        order_by = Object.publication_date.desc() if sort_order == 'desc' else Object.publication_date.asc()
    else:  # creation_date
        order_by = Object.creation_date.desc() if sort_order == 'desc' else Object.creation_date.asc()
    
    query = query.order_by(order_by)
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'objects': [obj.to_dict() for obj in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })


@user_routes_bp.route('/dashboard/objects/create', methods=['GET'])
@jwt_required
def user_create_object_page(current_user):
    """Create object page"""
    return render_template('user/create_object.html', user=current_user)


@user_routes_bp.route('/dashboard/objects/<object_id>', methods=['GET'])
@jwt_required
def user_get_object(object_id, current_user):
    """Get single object"""
    obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
    
    if not obj:
        return jsonify({'error': 'Object not found'}), 404
    
    return jsonify(obj.to_dict())


@user_routes_bp.route('/dashboard/objects/publish', methods=['POST'])
@jwt_required
def user_publish_object_via_bot(current_user):
    """Publish object via bot"""
    import requests
    import time
    from bot.config import BOT_TOKEN
    from app.models.chat import Chat
    from app.models.publication_history import PublicationHistory
    from bot.utils import (
        format_publication_text, get_districts_config, get_price_ranges
    )
    from bot.models import User as BotUser, Object as BotObject
    from bot.database import get_db as get_bot_db
    from datetime import timedelta
    
    data = request.get_json()
    object_id = data.get('object_id')
    
    if not object_id:
        return jsonify({'error': 'object_id is required'}), 400
    
    # Get object
    obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
    if not obj:
        return jsonify({'error': 'Object not found'}), 404
    
    # Check contacts
    phone = obj.phone_number or current_user.phone
    show_username = obj.show_username or False
    has_username = show_username and current_user.username
    
    if not phone and not has_username:
        return jsonify({
            'error': 'No contact information',
            'details': 'Please provide phone number or enable username display'
        }), 400
    
    if not BOT_TOKEN:
        return jsonify({'error': 'BOT_TOKEN is not configured'}), 500
    
    try:
        # Get bot user (try to find by web user's telegram_id if linked)
        bot_user = None
        bot_db = get_bot_db()
        try:
            # Try to find bot user by telegram_id if web user has it
            if hasattr(current_user, 'telegram_id') and current_user.telegram_id:
                bot_user = bot_db.query(BotUser).filter_by(telegram_id=int(current_user.telegram_id)).first()
        finally:
            bot_db.close()
        
        # Get bot object
        bot_db = get_bot_db()
        try:
            bot_obj = bot_db.query(BotObject).filter_by(object_id=object_id).first()
            if not bot_obj:
                # Create bot object from web object
                bot_obj = BotObject(
                    object_id=obj.object_id,
                    user_id=bot_user.user_id if bot_user else None,
                    rooms_type=obj.rooms_type,
                    price=obj.price,
                    districts_json=obj.districts_json,
                    region=obj.region,
                    city=obj.city,
                    photos_json=obj.photos_json,
                    area=obj.area,
                    floor=obj.floor,
                    address=obj.address,
                    renovation=obj.renovation,
                    comment=obj.comment,
                    contact_name=obj.contact_name,
                    show_username=obj.show_username,
                    phone_number=obj.phone_number,
                    status=obj.status,
                    source='web'
                )
                bot_db.add(bot_obj)
                bot_db.commit()
        finally:
            bot_db.close()
        
        # Format publication text
        publication_text = format_publication_text(bot_obj, bot_user, is_preview=False)
        
        # Get target chats (reuse logic from bot)
        target_chats = []
        bot_db = get_bot_db()
        try:
            from bot.models import Chat as BotChat
            chats = bot_db.query(BotChat).filter_by(owner_type='bot', is_active=True).all()
            
            rooms_type = obj.rooms_type or ""
            districts = obj.districts_json or []
            price = obj.price or 0
            
            districts_config = get_districts_config()
            
            # Add parent districts
            all_districts = set(districts)
            for district in districts:
                if isinstance(district, str) and district in districts_config:
                    parent_districts = districts_config[district]
                    if isinstance(parent_districts, list):
                        all_districts.update(parent_districts)
            
            for chat in chats:
                matches = False
                filters = chat.filters_json or {}
                
                # Check if filters_json is used
                has_filters_json = bool(filters.get('rooms_types') or filters.get('districts') or 
                                       filters.get('price_min') is not None or filters.get('price_max') is not None)
                
                if has_filters_json:
                    rooms_match = True
                    districts_match = True
                    price_match = True
                    
                    if filters.get('rooms_types'):
                        rooms_match = rooms_type in filters['rooms_types']
                    
                    if filters.get('districts'):
                        chat_districts = set(filters['districts'])
                        districts_match = bool(chat_districts.intersection(all_districts))
                    
                    price_min = filters.get('price_min')
                    price_max = filters.get('price_max')
                    if price_min is not None or price_max is not None:
                        price_min = price_min or 0
                        price_max = price_max if price_max is not None else float('inf')
                        price_match = price_min <= price < price_max
                    
                    if rooms_match and districts_match and price_match:
                        matches = True
                else:
                    # Legacy category support
                    category = chat.category or ""
                    
                    if category.startswith("rooms_") and category.replace("rooms_", "") == rooms_type:
                        matches = True
                    
                    if category.startswith("district_"):
                        district_name = category.replace("district_", "")
                        if district_name in all_districts:
                            matches = True
                    
                    if category.startswith("price_"):
                        try:
                            parts = category.replace("price_", "").split("_")
                            if len(parts) == 2:
                                min_price = float(parts[0])
                                max_price = float(parts[1])
                                if min_price <= price < max_price:
                                    matches = True
                        except:
                            pass
                
                if matches:
                    # Map bot chat_id to web chat_id
                    web_chat = Chat.query.filter_by(telegram_chat_id=chat.telegram_chat_id, owner_type='bot').first()
                    if web_chat and web_chat.chat_id not in target_chats:
                        target_chats.append(web_chat.chat_id)
        finally:
            bot_db.close()
        
        if not target_chats:
            return jsonify({
                'error': 'No matching chats',
                'details': 'No active chats match the object parameters'
            }), 400
        
        # Check if object was published within last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_publications = PublicationHistory.query.filter(
            PublicationHistory.object_id == object_id,
            PublicationHistory.chat_id.in_(target_chats),
            PublicationHistory.published_at >= yesterday,
            PublicationHistory.deleted == False
        ).all()
        
        if recent_publications:
            blocked_chats = [p.chat_id for p in recent_publications]
            return jsonify({
                'error': 'Object was already published to some chats within 24 hours',
                'blocked_chat_ids': blocked_chats
            }), 400
        
        # Publish to each chat
        published_count = 0
        errors = []
        url = f'https://api.telegram.org/bot{BOT_TOKEN}'
        
        for chat_id in target_chats:
            try:
                # Check publication history for this specific chat
                chat = Chat.query.filter_by(chat_id=chat_id).first()
                if not chat:
                    continue
                
                # Check if already published to this chat within 24 hours
                recent_pub = PublicationHistory.query.filter(
                    PublicationHistory.object_id == object_id,
                    PublicationHistory.chat_id == chat_id,
                    PublicationHistory.published_at >= yesterday,
                    PublicationHistory.deleted == False
                ).first()
                
                if recent_pub:
                    continue
                
                telegram_chat_id = chat.telegram_chat_id
                
                # Send message
                send_url = f'{url}/sendMessage'
                payload = {
                    'chat_id': telegram_chat_id,
                    'text': publication_text,
                    'parse_mode': 'HTML'
                }
                
                response = requests.post(send_url, json=payload, timeout=10)
                response.raise_for_status()
                result = response.json()
                
                if not result.get('ok'):
                    error_description = result.get('description', 'Unknown error')
                    errors.append(f"Chat {chat.title}: {error_description}")
                    continue
                
                # Update chat statistics and create publication history
                chat.total_publications = (chat.total_publications or 0) + 1
                chat.last_publication = datetime.utcnow()
                
                history = PublicationHistory(
                    object_id=object_id,
                    chat_id=chat_id,
                    account_id=None,  # Bot publication
                    published_at=datetime.utcnow(),
                    message_id=result.get('result', {}).get('message_id'),
                    deleted=False
                )
                db.session.add(history)
                
                published_count += 1
                
                # Rate limit: 20 messages per minute
                if published_count % 20 == 0:
                    time.sleep(60)
                else:
                    time.sleep(3)  # 3 seconds between messages
                
            except Exception as e:
                logger.error(f"Error publishing to chat {chat_id}: {e}", exc_info=True)
                errors.append(f"Chat {chat_id}: {str(e)}")
                continue
        
        # Update object status
        obj.status = "опубликовано"
        obj.publication_date = datetime.utcnow()
        db.session.commit()
        
        # Log action
        log_action(
            action='web_object_published_via_bot',
            user_id=current_user.user_id,
            details={
                'object_id': object_id,
                'chats_count': len(target_chats),
                'published_count': published_count,
                'errors': errors
            }
        )
        
        return jsonify({
            'success': True,
            'published_count': published_count,
            'total_chats': len(target_chats),
            'errors': errors if errors else None
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error publishing object via bot: {e}", exc_info=True)
        log_error(e, 'web_object_publish_via_bot_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({'error': str(e)}), 500
