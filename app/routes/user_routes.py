"""
User routes - реорганизованные пользовательские роуты
"""
from flask import Blueprint, request, jsonify, render_template
from app.database import db
from app.models.object import Object
from app.models.publication_queue import PublicationQueue
from app.models.publication_history import PublicationHistory
from app.models.telegram_account import TelegramAccount
from app.models.quick_access import QuickAccess
from app.models.autopublish_config import AutopublishConfig
from app.models.chat_group import ChatGroup
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
    
    # Objects on autopublication (objects with pending/scheduled autopublish queue items)
    autopublish_objects = db.session.query(func.count(func.distinct(PublicationQueue.object_id))).filter(
        PublicationQueue.user_id == current_user.user_id,
        PublicationQueue.mode == 'autopublish',
        PublicationQueue.status.in_(['pending', 'scheduled'])
    ).scalar() or 0
    
    return jsonify({
        'objects_count': objects_count,
        'objects_by_status': dict(objects_by_status),
        'today_publications': today_publications,
        'total_publications': total_publications,
        'accounts_count': accounts_count,
        'autopublish_objects_count': autopublish_objects
    })


@user_routes_bp.route('/dashboard/autopublish', methods=['GET'])
@jwt_required
def get_autopublish_config(current_user):
    """Get list of objects with autopublish settings and available objects to add"""
    # Get configs for current user
    configs = AutopublishConfig.query.filter_by(user_id=current_user.user_id).all()

    # Preload object data
    object_ids = [cfg.object_id for cfg in configs]
    objects_map = {}
    if object_ids:
        objects = Object.query.filter(
            Object.user_id == current_user.user_id,
            Object.object_id.in_(object_ids)
        ).all()
        objects_map = {obj.object_id: obj for obj in objects}

    # Build response list
    autopublish_items = []
    for cfg in configs:
        obj = objects_map.get(cfg.object_id)
        if not obj:
            continue

        item = {
            'object': obj.to_dict(),
            'config': cfg.to_dict(),
            # Для бота чаты подбираются автоматически по фильтрам,
            # поэтому явно не сохраняем их список в конфиге.
        }
        autopublish_items.append(item)

    # Available objects to add (не в архиве)
    used_ids = set(object_ids)
    available_objects = Object.query.filter(
        Object.user_id == current_user.user_id,
        Object.status != 'архив',
        ~Object.object_id.in_(used_ids)
    ).all()

    return jsonify({
        'autopublish_items': autopublish_items,
        'available_objects': [obj.to_dict() for obj in available_objects],
    })


@user_routes_bp.route('/dashboard/autopublish/<string:object_id>/chats', methods=['GET'])
@jwt_required
def get_autopublish_chats_for_object(object_id, current_user):
    """Get list of chats where object will be published (bot chats and user account chats)"""
    from app.models.chat import Chat
    from app.models.telegram_account import TelegramAccount
    from bot.utils import get_districts_config
    from bot.models import Chat as BotChat
    from bot.database import get_db as get_bot_db
    
    obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
    if not obj:
        return jsonify({'error': 'Object not found'}), 404
    
    cfg = AutopublishConfig.query.filter_by(
        user_id=current_user.user_id,
        object_id=object_id
    ).first()
    
    result = {
        'bot_chats': [],
        'user_chats': []
    }
    
    # Get bot chats that match object filters
    if cfg and cfg.bot_enabled:
        rooms_type = obj.rooms_type or ""
        districts = obj.districts_json or []
        price = obj.price or 0
        
        districts_config = get_districts_config()
        all_districts = set(districts)
        for district in districts:
            if isinstance(district, str) and district in districts_config:
                parent_districts = districts_config[district]
                if isinstance(parent_districts, list):
                    all_districts.update(parent_districts)
        
        bot_db = get_bot_db()
        try:
            bot_chats = bot_db.query(BotChat).filter_by(owner_type='bot', is_active=True).all()
            
            for bot_chat in bot_chats:
                matches = False
                
                # Check filters_json
                if bot_chat.filters_json:
                    filters = bot_chat.filters_json
                    rooms_match = True
                    districts_match = True
                    price_match = True
                    
                    rooms_types = filters.get('rooms_types', [])
                    if rooms_types and rooms_type not in rooms_types:
                        rooms_match = False
                    
                    filter_districts = filters.get('districts', [])
                    if filter_districts:
                        if not any(d in all_districts for d in filter_districts):
                            districts_match = False
                    
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
                    category = bot_chat.category or ""
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
                    web_chat = Chat.query.filter_by(telegram_chat_id=bot_chat.telegram_chat_id, owner_type='bot').first()
                    if web_chat:
                        result['bot_chats'].append({
                            'chat_id': web_chat.chat_id,
                            'title': web_chat.title,
                            'telegram_chat_id': web_chat.telegram_chat_id,
                            'type': 'bot'
                        })
        finally:
            bot_db.close()
    
    # Get user account chats from config
    if cfg and cfg.accounts_config_json:
        accounts_cfg = cfg.accounts_config_json
        accounts_list = accounts_cfg.get('accounts') if isinstance(accounts_cfg, dict) else []
        
        if isinstance(accounts_list, list):
            for acc_entry in accounts_list:
                account_id = acc_entry.get('account_id')
                chat_ids = acc_entry.get('chat_ids', [])
                
                if account_id and chat_ids:
                    account = TelegramAccount.query.get(account_id)
                    if account and account.owner_id == current_user.user_id:
                        chats = Chat.query.filter(
                            Chat.chat_id.in_(chat_ids),
                            Chat.owner_type == 'user',
                            Chat.owner_account_id == account_id
                        ).all()
                        
                        for chat in chats:
                            result['user_chats'].append({
                                'chat_id': chat.chat_id,
                                'title': chat.title,
                                'telegram_chat_id': chat.telegram_chat_id,
                                'type': 'user',
                                'account_id': account_id,
                                'account_phone': account.phone
                            })
    
    return jsonify(result)


@user_routes_bp.route('/dashboard/autopublish', methods=['POST'])
@jwt_required
def create_or_update_autopublish_config(current_user):
    """Create or update autopublish config for object"""
    data = request.get_json() or {}
    object_id = data.get('object_id')
    bot_enabled = bool(data.get('bot_enabled', True))
    accounts_config = data.get('accounts_config_json') or data.get('accounts_config')

    if not object_id:
        return jsonify({'error': 'object_id is required'}), 400

    obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
    if not obj:
        return jsonify({'error': 'Object not found'}), 404

    cfg = AutopublishConfig.query.filter_by(
        user_id=current_user.user_id,
        object_id=object_id
    ).first()

    if not cfg:
        cfg = AutopublishConfig(
            user_id=current_user.user_id,
            object_id=object_id,
        )
        db.session.add(cfg)

    # Бот всегда включен для автопубликации
    cfg.bot_enabled = True
    
    # Сохраняем настройки аккаунтов, если переданы
    if isinstance(accounts_config, dict):
        # Проверяем, что есть хотя бы один аккаунт с выбранными чатами
        accounts_list = accounts_config.get('accounts', [])
        has_valid_accounts = False
        for acc_entry in accounts_list:
            chat_ids = acc_entry.get('chat_ids', [])
            if chat_ids and len(chat_ids) > 0:
                has_valid_accounts = True
                break
        
        if has_valid_accounts:
            cfg.accounts_config_json = accounts_config
        else:
            # Если нет выбранных чатов, очищаем конфигурацию аккаунтов
            cfg.accounts_config_json = None
    elif accounts_config is None:
        # Не затираем существующие настройки, если ключ не передан
        pass
    
    # Автопубликация всегда включена (бот всегда включен)
    cfg.enabled = True

    try:
        db.session.commit()
        
        # Создаем очередь публикации сразу для объекта (если включена автопубликация)
        if cfg.enabled:
            from workers.tasks import _get_matching_bot_chats_for_object
            from app.models.chat import Chat as WebChat
            from bot.database import get_db as get_bot_db
            from bot.models import Object as BotObject, Chat as BotChat
            
            # Создаем очередь для бота (всегда включен)
            worker_db = get_bot_db()
            try:
                # Получаем или создаем объект в базе бота
                bot_obj = worker_db.query(BotObject).filter_by(object_id=object_id).first()
                if not bot_obj:
                    bot_obj = BotObject(
                        object_id=obj.object_id,
                        user_id=None,
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
                    worker_db.add(bot_obj)
                    worker_db.commit()
                
                bot_chats = _get_matching_bot_chats_for_object(worker_db, bot_obj)
                for bot_chat in bot_chats:
                    # Находим соответствующий чат в веб-базе
                    web_chat = WebChat.query.filter_by(
                        telegram_chat_id=bot_chat.telegram_chat_id,
                        owner_type='bot'
                    ).first()
                    if web_chat:
                        # Проверяем, нет ли уже такой очереди
                        existing = PublicationQueue.query.filter_by(
                            object_id=object_id,
                            chat_id=web_chat.chat_id,
                            type='bot',
                            mode='autopublish',
                            status='pending'
                        ).first()
                        if not existing:
                            queue = PublicationQueue(
                                object_id=object_id,
                                chat_id=web_chat.chat_id,
                                account_id=None,
                                user_id=current_user.user_id,
                                type='bot',
                                mode='autopublish',
                                status='pending',
                                created_at=datetime.utcnow(),
                            )
                            db.session.add(queue)
            finally:
                worker_db.close()
            
            # Создаем очередь для аккаунтов пользователей
            accounts_cfg = cfg.accounts_config_json or {}
            accounts_list = accounts_cfg.get('accounts') if isinstance(accounts_cfg, dict) else []
            if isinstance(accounts_list, list):
                for acc_entry in accounts_list:
                    account_id = acc_entry.get('account_id')
                    chat_ids = acc_entry.get('chat_ids', [])
                    if account_id and chat_ids:
                        account = TelegramAccount.query.get(account_id)
                        if account and account.owner_id == current_user.user_id and account.is_active:
                            for chat_id in chat_ids:
                                chat = WebChat.query.get(chat_id)
                                if chat and chat.owner_type == 'user' and chat.owner_account_id == account_id:
                                    # Проверяем, нет ли уже такой очереди
                                    existing = PublicationQueue.query.filter_by(
                                        object_id=object_id,
                                        chat_id=chat_id,
                                        type='user',
                                        mode='autopublish',
                                        status='pending'
                                    ).first()
                                    if not existing:
                                        queue = PublicationQueue(
                                            object_id=object_id,
                                            chat_id=chat_id,
                                            account_id=account_id,
                                            user_id=current_user.user_id,
                                            type='user',
                                            mode='autopublish',
                                            status='pending',
                                            created_at=datetime.utcnow(),
                                        )
                                        db.session.add(queue)
            
            db.session.commit()
        return jsonify({'success': True, 'config': cfg.to_dict()})
    except Exception as e:
        db.session.rollback()
        log_error(e, 'autopublish_config_save_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({'error': str(e)}), 500


@user_routes_bp.route('/dashboard/autopublish/<string:object_id>', methods=['PUT'])
@jwt_required
def update_autopublish_config(object_id, current_user):
    """Update existing autopublish config (enable/disable, bot_enabled, accounts)"""
    cfg = AutopublishConfig.query.filter_by(
        user_id=current_user.user_id,
        object_id=object_id
    ).first()

    if not cfg:
        return jsonify({'error': 'Config not found'}), 404

    data = request.get_json() or {}

    # Бот всегда включен - игнорируем bot_enabled из запроса
    cfg.bot_enabled = True
    
    if 'accounts_config_json' in data or 'accounts_config' in data:
        accounts_config = data.get('accounts_config_json') or data.get('accounts_config')
        if isinstance(accounts_config, dict):
            # Проверяем, что есть хотя бы один аккаунт с выбранными чатами
            accounts_list = accounts_config.get('accounts', [])
            has_valid_accounts = False
            for acc_entry in accounts_list:
                chat_ids = acc_entry.get('chat_ids', [])
                if chat_ids and len(chat_ids) > 0:
                    has_valid_accounts = True
                    break
            
            if has_valid_accounts:
                cfg.accounts_config_json = accounts_config
            else:
                # Если нет выбранных чатов, очищаем конфигурацию аккаунтов
                cfg.accounts_config_json = None
                return jsonify({
                    'error': 'Сначала выберите чаты для аккаунтов',
                    'details': 'Нельзя включить автопубликацию через аккаунты без выбранных чатов'
                }), 400
        elif accounts_config is None:
            cfg.accounts_config_json = None

    # Автопубликация всегда включена (бот всегда включен)
    cfg.enabled = True

    try:
        db.session.commit()
        
        # Создаем/обновляем очередь публикации для объекта
        obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
        if obj and cfg.enabled:
            from workers.tasks import _get_matching_bot_chats_for_object
            from app.models.chat import Chat as WebChat
            from bot.database import get_db as get_bot_db
            from bot.models import Object as BotObject, Chat as BotChat
            
            # Создаем очередь для бота (всегда включен)
            worker_db = get_bot_db()
            try:
                # Получаем или создаем объект в базе бота
                bot_obj = worker_db.query(BotObject).filter_by(object_id=object_id).first()
                if not bot_obj:
                    bot_obj = BotObject(
                        object_id=obj.object_id,
                        user_id=None,
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
                    worker_db.add(bot_obj)
                    worker_db.commit()
                
                bot_chats = _get_matching_bot_chats_for_object(worker_db, bot_obj)
                for bot_chat in bot_chats:
                    # Находим соответствующий чат в веб-базе
                    web_chat = WebChat.query.filter_by(
                        telegram_chat_id=bot_chat.telegram_chat_id,
                        owner_type='bot'
                    ).first()
                    if web_chat:
                        # Проверяем, нет ли уже такой очереди
                        existing = PublicationQueue.query.filter_by(
                            object_id=object_id,
                            chat_id=web_chat.chat_id,
                            type='bot',
                            mode='autopublish',
                            status='pending'
                        ).first()
                        if not existing:
                            queue = PublicationQueue(
                                object_id=object_id,
                                chat_id=web_chat.chat_id,
                                account_id=None,
                                user_id=current_user.user_id,
                                type='bot',
                                mode='autopublish',
                                status='pending',
                                created_at=datetime.utcnow(),
                            )
                            db.session.add(queue)
            finally:
                worker_db.close()
            
            # Создаем очередь для аккаунтов пользователей
            accounts_cfg = cfg.accounts_config_json or {}
            accounts_list = accounts_cfg.get('accounts') if isinstance(accounts_cfg, dict) else []
            if isinstance(accounts_list, list):
                for acc_entry in accounts_list:
                    account_id = acc_entry.get('account_id')
                    chat_ids = acc_entry.get('chat_ids', [])
                    if account_id and chat_ids:
                        account = TelegramAccount.query.get(account_id)
                        if account and account.owner_id == current_user.user_id and account.is_active:
                            for chat_id in chat_ids:
                                chat = WebChat.query.get(chat_id)
                                if chat and chat.owner_type == 'user' and chat.owner_account_id == account_id:
                                    # Проверяем, нет ли уже такой очереди
                                    existing = PublicationQueue.query.filter_by(
                                        object_id=object_id,
                                        chat_id=chat_id,
                                        type='user',
                                        mode='autopublish',
                                        status='pending'
                                    ).first()
                                    if not existing:
                                        queue = PublicationQueue(
                                            object_id=object_id,
                                            chat_id=chat_id,
                                            account_id=account_id,
                                            user_id=current_user.user_id,
                                            type='user',
                                            mode='autopublish',
                                            status='pending',
                                            created_at=datetime.utcnow(),
                                        )
                                        db.session.add(queue)
            
            db.session.commit()
        
        return jsonify({'success': True, 'config': cfg.to_dict()})
    except Exception as e:
        db.session.rollback()
        log_error(e, 'autopublish_config_update_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({'error': str(e)}), 500


@user_routes_bp.route('/dashboard/autopublish/<string:object_id>', methods=['DELETE'])
@jwt_required
def delete_autopublish_config(object_id, current_user):
    """Delete autopublish config for object"""
    cfg = AutopublishConfig.query.filter_by(
        user_id=current_user.user_id,
        object_id=object_id
    ).first()

    if not cfg:
        return jsonify({'error': 'Config not found'}), 404

    try:
        db.session.delete(cfg)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        log_error(e, 'autopublish_config_delete_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({'error': str(e)}), 500


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
    district = request.args.get('district')
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
    if district:
        # Filter by district in districts_json array (PostgreSQL JSONB)
        # Use JSONB contains operator for array filtering
        query = query.filter(Object.districts_json.contains([district]))
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
    elif sort_by == 'creation_date':
        order_by = Object.creation_date.desc() if sort_order == 'desc' else Object.creation_date.asc()
    elif sort_by == 'publication_date':
        order_by = Object.publication_date.desc() if sort_order == 'desc' else Object.publication_date.asc()
    else:  # default to creation_date
        order_by = Object.creation_date.desc() if sort_order == 'desc' else Object.creation_date.asc()
    
    query = query.order_by(order_by)
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Add can_publish info for each object
    from datetime import timedelta
    yesterday = datetime.utcnow() - timedelta(days=1)
    objects_list = []
    for obj in pagination.items:
        obj_dict = obj.to_dict()
        # Check if can publish (not published within last 24 hours)
        recent_publications = PublicationHistory.query.filter(
            PublicationHistory.object_id == obj.object_id,
            PublicationHistory.published_at >= yesterday,
            PublicationHistory.deleted == False
        ).all()
        
        obj_dict['can_publish'] = len(recent_publications) == 0
        if recent_publications:
            last_pub = max(recent_publications, key=lambda p: p.published_at)
            obj_dict['last_publication'] = last_pub.published_at.isoformat()
        objects_list.append(obj_dict)
    
    return jsonify({
        'objects': objects_list,
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
    
    # Check if can publish (not published within last 24 hours)
    from datetime import timedelta
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_publications = PublicationHistory.query.filter(
        PublicationHistory.object_id == object_id,
        PublicationHistory.published_at >= yesterday,
        PublicationHistory.deleted == False
    ).all()
    
    can_publish = len(recent_publications) == 0
    last_publication = None
    if recent_publications:
        last_pub = max(recent_publications, key=lambda p: p.published_at)
        last_publication = last_pub.published_at.isoformat()
    
    obj_dict = obj.to_dict()
    obj_dict['can_publish'] = can_publish
    obj_dict['last_publication'] = last_publication
    
    return jsonify(obj_dict)


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
            'errors': errors if errors else None,
            'message': f'Объект успешно опубликован в {published_count} из {len(target_chats)} чатов'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error publishing object via bot: {e}", exc_info=True)
        log_error(e, 'web_object_publish_via_bot_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({'error': str(e)}), 500


@user_routes_bp.route('/dashboard/objects/<object_id>/preview', methods=['POST'])
@jwt_required
def user_preview_object_in_bot(object_id, current_user):
    """Send preview of object to user via bot"""
    import requests
    from bot.config import BOT_TOKEN
    from bot.utils import format_publication_text
    from bot.models import User as BotUser, Object as BotObject
    from bot.database import get_db as get_bot_db
    
    # Get object
    obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
    if not obj:
        return jsonify({'error': 'Object not found'}), 404
    
    # Check if user has telegram_id
    if not hasattr(current_user, 'telegram_id') or not current_user.telegram_id:
        return jsonify({
            'error': 'Telegram ID not found',
            'details': 'Please connect your Telegram account first'
        }), 400
    
    if not BOT_TOKEN:
        return jsonify({'error': 'BOT_TOKEN is not configured'}), 500
    
    try:
        # Get bot user
        bot_user = None
        bot_db = get_bot_db()
        try:
            bot_user = bot_db.query(BotUser).filter_by(telegram_id=int(current_user.telegram_id)).first()
        finally:
            bot_db.close()
        
        # Get or create bot object
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
        
        # Format publication text with preview flag
        publication_text = format_publication_text(bot_obj, bot_user, is_preview=True)
        
        # Send message to user via bot
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
        payload = {
            'chat_id': int(current_user.telegram_id),
            'text': publication_text,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if not result.get('ok'):
            error_description = result.get('description', 'Unknown error')
            return jsonify({
                'error': f'Failed to send preview: {error_description}',
                'details': 'Make sure you have started a conversation with the bot'
            }), 500
        
        message_id = result.get('result', {}).get('message_id')
        
        # Log action
        log_action(
            action='web_object_preview_sent',
            user_id=current_user.user_id,
            details={
                'object_id': object_id,
                'message_id': message_id
            }
        )
        
        return jsonify({
            'success': True,
            'message': 'Превью отправлено в Telegram',
            'message_id': message_id
        }), 200
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending preview: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to send preview',
            'details': str(e)
        }), 500
    except Exception as e:
        logger.error(f"Error in preview: {e}", exc_info=True)
        log_error(e, 'user_preview_object_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@user_routes_bp.route('/dashboard/settings', methods=['GET'])
@jwt_required
def user_settings_page(current_user):
    """User settings page"""
    return render_template('user/settings.html', user=current_user)


@user_routes_bp.route('/dashboard/districts', methods=['GET'])
@jwt_required
def get_user_districts(current_user):
    """Get all districts for user forms"""
    from app.models.system_setting import SystemSetting
    
    districts_setting = SystemSetting.query.filter_by(key='districts_config').first()
    districts_config = districts_setting.value_json if districts_setting else {}
    
    # Convert dict to list of district names
    districts_list = list(districts_config.keys()) if isinstance(districts_config, dict) else []
    
    return jsonify({
        'districts': districts_list
    })


@user_routes_bp.route('/dashboard/settings/data', methods=['GET'])
@jwt_required
def get_user_settings(current_user):
    """Get user settings"""
    settings = current_user.settings_json or {}
    return jsonify({
        'phone': current_user.phone or '',
        'contact_name': settings.get('contact_name', ''),
        'default_show_username': settings.get('default_show_username', False)
    })


@user_routes_bp.route('/dashboard/settings/data', methods=['PUT'])
@jwt_required
def update_user_settings(current_user):
    """Update user settings"""
    data = request.get_json()
    
    # Validate phone number format if provided
    if 'phone' in data and data['phone']:
        phone = data['phone'].strip()
        import re
        phone_pattern = re.compile(r'^8\d{10}$')
        if not phone_pattern.match(phone):
            return jsonify({
                'error': 'Некорректный номер телефона',
                'details': 'Номер должен быть в формате 89693386969 (11 цифр, начинается с 8)'
            }), 400
        current_user.phone = phone
    elif 'phone' in data:
        current_user.phone = None
    
    if not current_user.settings_json:
        current_user.settings_json = {}
    
    # Создаем новый словарь для отслеживания изменений SQLAlchemy
    settings = dict(current_user.settings_json) if current_user.settings_json else {}
    
    if 'contact_name' in data:
        settings['contact_name'] = data['contact_name'] or ''
    
    if 'default_show_username' in data:
        settings['default_show_username'] = bool(data['default_show_username'])
    
    current_user.settings_json = settings
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(current_user, 'settings_json')
    
    try:
        db.session.commit()
        
        log_action(
            action='user_settings_updated',
            user_id=current_user.user_id,
            details={
                'updated_fields': list(data.keys())
            }
        )
        
        # Перезагружаем пользователя для получения актуальных данных
        db.session.refresh(current_user)
        settings = current_user.settings_json or {}
        
        return jsonify({
            'phone': current_user.phone or '',
            'contact_name': settings.get('contact_name', ''),
            'default_show_username': settings.get('default_show_username', False)
        })
    except Exception as e:
        db.session.rollback()
        log_error(e, 'user_settings_update_failed', current_user.user_id, {})
        return jsonify({'error': str(e)}), 500