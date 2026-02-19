"""
User routes - реорганизованные пользовательские роуты
"""
from flask import Blueprint, request, jsonify, render_template
from app.database import db
from app.models.object import Object
from app.models.publication_queue import PublicationQueue
from app.models.account_publication_queue import AccountPublicationQueue
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
    
    # Objects on autopublication (objects with enabled autopublish config)
    from app.models.autopublish_config import AutopublishConfig
    autopublish_objects = AutopublishConfig.query.filter_by(
        user_id=current_user.user_id,
        enabled=True
    ).count()
    
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

        # Определяем ближайшее время публикации для бота (общая очередь бота)
        next_bot_queue = PublicationQueue.query.filter(
            PublicationQueue.user_id == current_user.user_id,
            PublicationQueue.object_id == cfg.object_id,
            PublicationQueue.type == 'bot',
            PublicationQueue.mode == 'autopublish',
            PublicationQueue.status == 'pending'
        ).order_by(
            PublicationQueue.scheduled_time.asc().nullslast(),
            PublicationQueue.created_at.asc()
        ).first()

        # Определяем ближайшее время публикации через аккаунты пользователя
        next_user_queue = PublicationQueue.query.filter(
            PublicationQueue.user_id == current_user.user_id,
            PublicationQueue.object_id == cfg.object_id,
            PublicationQueue.type == 'user',
            PublicationQueue.mode == 'autopublish',
            PublicationQueue.status == 'pending'
        ).order_by(
            PublicationQueue.scheduled_time.asc().nullslast(),
            PublicationQueue.created_at.asc()
        ).first()

        item = {
            'object': obj.to_dict(),
            'config': cfg.to_dict(),
            # Для бота чаты подбираются автоматически по фильтрам,
            # поэтому явно не сохраняем их список в конфиге.
            'next_bot_publication_time': next_bot_queue.scheduled_time.isoformat() if next_bot_queue and next_bot_queue.scheduled_time else None,
            'next_user_publication_time': next_user_queue.scheduled_time.isoformat() if next_user_queue and next_user_queue.scheduled_time else None,
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


@user_routes_bp.route('/dashboard/autopublish/<string:object_id>', methods=['GET'])
@jwt_required
def get_autopublish_config_for_object(object_id, current_user):
    """Get autopublish config for specific object"""
    cfg = AutopublishConfig.query.filter_by(
        user_id=current_user.user_id,
        object_id=object_id
    ).first()
    
    if not cfg:
        return jsonify({
            'enabled': False,
            'bot_enabled': False,
            'accounts_config_json': {}
        }), 200
    
    return jsonify(cfg.to_dict()), 200


@user_routes_bp.route('/dashboard/autopublish/<string:object_id>/chats', methods=['GET'])
@jwt_required
def get_autopublish_chats_for_object(object_id, current_user):
    """Get list of chats where object will be published (bot chats and user account chats)"""
    from app.models.chat import Chat
    from app.models.telegram_account import TelegramAccount
    from bot.utils import get_districts_config
    from bot.models import Chat as BotChat
    
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
        
        bot_chats = db.session.query(BotChat).filter_by(owner_type='bot', is_active=True).all()
        
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
                                'account_phone': account.phone,
                                'category': chat.category,
                                'filters_json': chat.filters_json
                            })
    
    # Добавляем информацию о группах чатов (только для автопубликации)
    from app.models.chat_group import ChatGroup
    user_groups = ChatGroup.query.filter_by(
        user_id=current_user.user_id,
        purpose='autopublish'
    ).all()
    result['chat_groups'] = []
    for group in user_groups:
        group_chats = [c for c in result['user_chats'] if c['chat_id'] in group.chat_ids]
        if group_chats:
            result['chat_groups'].append({
                'group_id': group.group_id,
                'name': group.name,
                'description': group.description,
                'category': group.category,
                'filters_json': group.filters_json,
                'chats': group_chats
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
        # Разрешаем сохранение формата публикации даже без выбранных чатов
        # Проверяем, что есть хотя бы один аккаунт с выбранными чатами только если есть аккаунты
        accounts_list = accounts_config.get('accounts', [])
        has_valid_accounts = False
        if accounts_list:
            for acc_entry in accounts_list:
                chat_ids = acc_entry.get('chat_ids', [])
                if chat_ids and len(chat_ids) > 0:
                    has_valid_accounts = True
                    break
        
        # Сохраняем конфигурацию если есть валидные аккаунты или если есть только формат публикации
        if has_valid_accounts or accounts_config.get('publication_format'):
            cfg.accounts_config_json = accounts_config
        elif accounts_list and len(accounts_list) > 0:
            # Если есть аккаунты, но нет выбранных чатов, очищаем конфигурацию аккаунтов
            # Но сохраняем формат публикации, если он есть
            if accounts_config.get('publication_format'):
                cfg.accounts_config_json = {'publication_format': accounts_config.get('publication_format'), 'accounts': []}
            else:
                cfg.accounts_config_json = None
        else:
            # Если нет аккаунтов, но есть формат публикации, сохраняем только формат
            if accounts_config.get('publication_format'):
                cfg.accounts_config_json = {'publication_format': accounts_config.get('publication_format'), 'accounts': []}
            else:
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
            from bot.models import Object as BotObject, Chat as BotChat
            
            # Создаем очередь для бота (всегда включен)
            # Получаем или создаем объект в базе бота
            bot_obj = db.session.query(BotObject).filter_by(object_id=object_id).first()
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
                    residential_complex=obj.residential_complex,
                    renovation=obj.renovation,
                    comment=obj.comment,
                    contact_name=obj.contact_name,
                    show_username=obj.show_username,
                    phone_number=obj.phone_number,
                    contact_name_2=obj.contact_name_2,
                    phone_number_2=obj.phone_number_2,
                    status=obj.status,
                    source='web'
                )
                db.session.add(bot_obj)
                db.session.commit()
            
            bot_chats = _get_matching_bot_chats_for_object(db.session, bot_obj)
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
                        # Получаем время для публикации (8:00-22:00 МСК)
                        from app.utils.time_utils import get_next_allowed_time_msk, msk_to_utc, get_moscow_time
                        now_msk = get_moscow_time()
                        scheduled_time_msk = get_next_allowed_time_msk(now_msk)
                        scheduled_time_utc = msk_to_utc(scheduled_time_msk)
                        
                        queue = PublicationQueue(
                            object_id=object_id,
                            chat_id=web_chat.chat_id,
                            account_id=None,
                            user_id=current_user.user_id,
                            type='bot',
                            mode='autopublish',
                            status='pending',
                            scheduled_time=scheduled_time_utc,
                            created_at=datetime.utcnow(),
                        )
                        db.session.add(queue)
            
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
                                    # Проверяем, нет ли уже такой очереди в AccountPublicationQueue
                                    existing = AccountPublicationQueue.query.filter_by(
                                        object_id=object_id,
                                        chat_id=chat_id,
                                        account_id=account_id,
                                        status='pending'
                                    ).first()
                                    if not existing:
                                        # Получаем время для публикации (8:00-22:00 МСК)
                                        from app.utils.time_utils import get_next_allowed_time_msk, msk_to_utc
                                        from bot.utils import get_moscow_time
                                        now_msk = get_moscow_time()
                                        scheduled_time_msk = get_next_allowed_time_msk(now_msk)
                                        scheduled_time_utc = msk_to_utc(scheduled_time_msk)
                                        
                                        queue = AccountPublicationQueue(
                                            object_id=object_id,
                                            chat_id=chat_id,
                                            account_id=account_id,
                                            user_id=current_user.user_id,
                                            status='pending',
                                            scheduled_time=scheduled_time_utc,
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
            # Унифицированная логика с create_or_update_autopublish_config:
            # разрешаем сохранять формат публикации даже без выбранных чатов
            accounts_list = accounts_config.get('accounts', [])
            has_valid_accounts = False

            if accounts_list:
                for acc_entry in accounts_list:
                    chat_ids = acc_entry.get('chat_ids', [])
                    if chat_ids and len(chat_ids) > 0:
                        has_valid_accounts = True
                        break

            if has_valid_accounts or accounts_config.get('publication_format'):
                # Есть валидные аккаунты с чатами ИЛИ хотя бы формат публикации
                cfg.accounts_config_json = accounts_config
            elif accounts_list and len(accounts_list) > 0:
                # Есть аккаунты, но нет выбранных чатов
                # Очищаем список аккаунтов, но при наличии сохраняем формат
                if accounts_config.get('publication_format'):
                    cfg.accounts_config_json = {
                        'publication_format': accounts_config.get('publication_format'),
                        'accounts': []
                    }
                else:
                    cfg.accounts_config_json = None
            else:
                # Нет аккаунтов, но можем сохранить только формат публикации
                if accounts_config.get('publication_format'):
                    cfg.accounts_config_json = {
                        'publication_format': accounts_config.get('publication_format'),
                        'accounts': []
                    }
                else:
                    cfg.accounts_config_json = None
        elif accounts_config is None:
            # Явное обнуление конфигурации аккаунтов
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
            from bot.models import Object as BotObject, Chat as BotChat
            
            # Создаем очередь для бота (всегда включен)
            # Получаем или создаем объект в базе бота
            bot_obj = db.session.query(BotObject).filter_by(object_id=object_id).first()
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
                    residential_complex=obj.residential_complex,
                    renovation=obj.renovation,
                    comment=obj.comment,
                    contact_name=obj.contact_name,
                    show_username=obj.show_username,
                    phone_number=obj.phone_number,
                    contact_name_2=obj.contact_name_2,
                    phone_number_2=obj.phone_number_2,
                    status=obj.status,
                    source='web'
                )
                db.session.add(bot_obj)
                db.session.commit()
            
            bot_chats = _get_matching_bot_chats_for_object(db.session, bot_obj)
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
                        # Получаем время для публикации (8:00-22:00 МСК)
                        from app.utils.time_utils import get_next_allowed_time_msk, msk_to_utc, get_moscow_time
                        now_msk = get_moscow_time()
                        scheduled_time_msk = get_next_allowed_time_msk(now_msk)
                        scheduled_time_utc = msk_to_utc(scheduled_time_msk)
                        
                        queue = PublicationQueue(
                            object_id=object_id,
                            chat_id=web_chat.chat_id,
                            account_id=None,
                            user_id=current_user.user_id,
                            type='bot',
                            mode='autopublish',
                            status='pending',
                            scheduled_time=scheduled_time_utc,
                            created_at=datetime.utcnow(),
                        )
                        db.session.add(queue)
            
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
                                    # Проверяем, нет ли уже такой очереди в AccountPublicationQueue
                                    existing = AccountPublicationQueue.query.filter_by(
                                        object_id=object_id,
                                        chat_id=chat_id,
                                        account_id=account_id,
                                        status='pending'
                                    ).first()
                                    if not existing:
                                        # Получаем время для публикации (8:00-22:00 МСК)
                                        from app.utils.time_utils import get_next_allowed_time_msk, msk_to_utc
                                        from bot.utils import get_moscow_time
                                        now_msk = get_moscow_time()
                                        scheduled_time_msk = get_next_allowed_time_msk(now_msk)
                                        scheduled_time_utc = msk_to_utc(scheduled_time_msk)
                                        
                                        queue = AccountPublicationQueue(
                                            object_id=object_id,
                                            chat_id=chat_id,
                                            account_id=account_id,
                                            user_id=current_user.user_id,
                                            status='pending',
                                            scheduled_time=scheduled_time_utc,
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
    # Проверка не применяется для админов (они могут публиковать без ограничений)
    objects_list = []
    for obj in pagination.items:
        obj_dict = obj.to_dict()
        
        if current_user.web_role != 'admin':
            # Check if can publish (not published within last 24 hours)
            from datetime import timedelta
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_publications = PublicationHistory.query.filter(
                PublicationHistory.object_id == obj.object_id,
                PublicationHistory.published_at >= yesterday,
                PublicationHistory.deleted == False
            ).all()
            
            obj_dict['can_publish'] = len(recent_publications) == 0
            if recent_publications:
                last_pub = max(recent_publications, key=lambda p: p.published_at)
                obj_dict['last_publication'] = last_pub.published_at.isoformat()
        else:
            # Админы всегда могут публиковать
            obj_dict['can_publish'] = True
        
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
    # Проверка не применяется для админов (они могут публиковать без ограничений)
    can_publish = True
    last_publication = None
    
    if current_user.web_role != 'admin':
        from datetime import timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_publications = PublicationHistory.query.filter(
            PublicationHistory.object_id == object_id,
            PublicationHistory.published_at >= yesterday,
            PublicationHistory.deleted == False
        ).all()
        
        can_publish = len(recent_publications) == 0
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
        if hasattr(current_user, 'telegram_id') and current_user.telegram_id:
            bot_user = db.session.query(BotUser).filter_by(telegram_id=int(current_user.telegram_id)).first()
        
        # Get bot object
        bot_obj = db.session.query(BotObject).filter_by(object_id=object_id).first()
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
                    residential_complex=obj.residential_complex,
                    renovation=obj.renovation,
                    comment=obj.comment,
                    contact_name=obj.contact_name,
                    show_username=obj.show_username,
                    phone_number=obj.phone_number,
                    contact_name_2=obj.contact_name_2,
                    phone_number_2=obj.phone_number_2,
                    status=obj.status,
                    source='web'
                )
                db.session.add(bot_obj)
                db.session.commit()
        
        # Получаем формат публикации из конфигурации автопубликации
        publication_format = 'default'
        from app.models.autopublish_config import AutopublishConfig
        autopublish_cfg = AutopublishConfig.query.filter_by(
            object_id=object_id,
            user_id=current_user.user_id
        ).first()
        if autopublish_cfg and autopublish_cfg.accounts_config_json:
            accounts_cfg = autopublish_cfg.accounts_config_json
            if isinstance(accounts_cfg, dict):
                publication_format = accounts_cfg.get('publication_format', 'default')
        
        # Format publication text
        publication_text = format_publication_text(bot_obj, bot_user, is_preview=False, publication_format=publication_format)
        
        # Get target chats (reuse logic from bot)
        target_chats = []
        from bot.models import Chat as BotChat
        chats = db.session.query(BotChat).filter_by(owner_type='bot', is_active=True).all()
        
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
            
            # Проверка типа привязки "общий" - такой чат получает все посты
            binding_type = filters.get('binding_type')
            if binding_type == 'common':
                # Map bot chat_id to web chat_id
                web_chat = Chat.query.filter_by(telegram_chat_id=chat.telegram_chat_id, owner_type='bot').first()
                if web_chat and web_chat.chat_id not in target_chats:
                    target_chats.append(web_chat.chat_id)
                continue  # Пропускаем проверку фильтров для "общего" чата
            
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
        
        if not target_chats:
            return jsonify({
                'error': 'No matching chats',
                'details': 'No active chats match the object parameters'
            }), 400
        
        # Check if object was published within last 24 hours
        # Проверка не применяется для админов (они могут публиковать без ограничений)
        if current_user.web_role != 'admin':
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
                # Проверка не применяется для админов (они могут публиковать без ограничений)
                if current_user.web_role != 'admin':
                    yesterday = datetime.utcnow() - timedelta(days=1)
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
        if hasattr(current_user, 'telegram_id') and current_user.telegram_id:
            bot_user = db.session.query(BotUser).filter_by(telegram_id=int(current_user.telegram_id)).first()
        
        # Get or create bot object
        bot_obj = db.session.query(BotObject).filter_by(object_id=object_id).first()
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
                    residential_complex=obj.residential_complex,
                    renovation=obj.renovation,
                    comment=obj.comment,
                    contact_name=obj.contact_name,
                    show_username=obj.show_username,
                    phone_number=obj.phone_number,
                    contact_name_2=obj.contact_name_2,
                    phone_number_2=obj.phone_number_2,
                    status=obj.status,
                    source='web'
                )
                db.session.add(bot_obj)
                db.session.commit()
        
        # Получаем формат публикации из конфигурации автопубликации
        publication_format = 'default'
        from app.models.autopublish_config import AutopublishConfig
        autopublish_cfg = AutopublishConfig.query.filter_by(
            object_id=object_id,
            user_id=current_user.user_id
        ).first()
        if autopublish_cfg and autopublish_cfg.accounts_config_json:
            accounts_cfg = autopublish_cfg.accounts_config_json
            if isinstance(accounts_cfg, dict):
                publication_format = accounts_cfg.get('publication_format', 'default')
        
        # Format publication text with preview flag
        publication_text = format_publication_text(bot_obj, bot_user, is_preview=True, publication_format=publication_format)
        
        # Send message to user via bot - всегда отправляем фото если оно есть
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
                
                logger.info(f"Trying to send photo: photo_path={photo_path}, full_path={full_path}, exists={os.path.exists(full_path)}")
                if os.path.exists(full_path):
                    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto'
                    with open(full_path, 'rb') as photo_file:
                        files = {'photo': photo_file}
                        payload = {
                            'chat_id': int(current_user.telegram_id),
                            'caption': publication_text,
                            'parse_mode': 'HTML'
                        }
                        response = requests.post(url, files=files, data=payload, timeout=30)
                else:
                    logger.warning(f"Photo file not found: {full_path}, sending text only")
                    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
                    payload = {
                        'chat_id': int(current_user.telegram_id),
                        'text': publication_text,
                        'parse_mode': 'HTML'
                    }
                    response = requests.post(url, json=payload, timeout=10)
            else:
                # Если путь не найден - отправляем только текст
                url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
                payload = {
                    'chat_id': int(current_user.telegram_id),
                    'text': publication_text,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, json=payload, timeout=10)
        else:
            # Если фото нет - отправляем только текст
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


@user_routes_bp.route('/dashboard/settings/clear-autopublish', methods=['POST'])
@jwt_required
def clear_autopublish_and_queues(current_user):
    """Clear all autopublish configs and queues for user"""
    try:
        # Удаляем все конфигурации автопубликации пользователя
        autopublish_configs = AutopublishConfig.query.filter_by(user_id=current_user.user_id).all()
        configs_count = len(autopublish_configs)
        for config in autopublish_configs:
            db.session.delete(config)
        
        # Получаем ID всех очередей публикаций с автопубликацией для пользователя
        # Используем no_autoflush, чтобы избежать преждевременного flush
        with db.session.no_autoflush:
            publication_queues = PublicationQueue.query.filter_by(
                user_id=current_user.user_id,
                mode='autopublish'
            ).all()
            queues_count = len(publication_queues)
            queue_ids = [q.queue_id for q in publication_queues]
        
        # Сначала обнуляем ссылки в PublicationHistory, чтобы избежать нарушения внешнего ключа
        if queue_ids:
            PublicationHistory.query.filter(
                PublicationHistory.queue_id.in_(queue_ids)
            ).update({PublicationHistory.queue_id: None}, synchronize_session=False)
            db.session.commit()  # Фиксируем обнуление ссылок
        
        # Теперь удаляем очереди
        if queue_ids:
            PublicationQueue.query.filter(
                PublicationQueue.queue_id.in_(queue_ids)
            ).delete(synchronize_session=False)
        
        # Получаем ID всех очередей публикаций для аккаунтов пользователя
        with db.session.no_autoflush:
            account_queues = AccountPublicationQueue.query.filter_by(user_id=current_user.user_id).all()
            account_queues_count = len(account_queues)
            account_queue_ids = [q.queue_id for q in account_queues]
        
        # Проверяем, есть ли модель AppPublicationHistory, которая может ссылаться на AccountPublicationQueue
        # Если есть, обнуляем ссылки
        try:
            from app.models.app_publication_history import AppPublicationHistory
            if account_queue_ids:
                # Проверяем, есть ли поле queue_id в AppPublicationHistory
                if hasattr(AppPublicationHistory, 'queue_id'):
                    AppPublicationHistory.query.filter(
                        AppPublicationHistory.queue_id.in_(account_queue_ids)
                    ).update({AppPublicationHistory.queue_id: None}, synchronize_session=False)
                    db.session.commit()  # Фиксируем обнуление ссылок
        except ImportError:
            # Модель не существует или не импортируется - пропускаем
            pass
        
        # Удаляем очереди для аккаунтов
        if account_queue_ids:
            AccountPublicationQueue.query.filter(
                AccountPublicationQueue.queue_id.in_(account_queue_ids)
            ).delete(synchronize_session=False)
        
        db.session.commit()
        
        log_action(
            action='autopublish_cleared',
            user_id=current_user.user_id,
            details={
                'configs_deleted': configs_count,
                'publication_queues_deleted': queues_count,
                'account_queues_deleted': account_queues_count
            }
        )
        
        return jsonify({
            'success': True,
            'message': 'Автопубликация и очереди успешно очищены',
            'deleted': {
                'configs': configs_count,
                'publication_queues': queues_count,
                'account_queues': account_queues_count
            }
        })
    except Exception as e:
        db.session.rollback()
        log_error(e, 'clear_autopublish_failed', current_user.user_id, {})
        return jsonify({'error': str(e)}), 500