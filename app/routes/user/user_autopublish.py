"""
User autopublish routes
Логика: управление автопубликацией объектов
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

user_autopublish_bp = Blueprint('user_autopublish', __name__)
logger = logging.getLogger(__name__)

@user_autopublish_bp.route('/dashboard/autopublish', methods=['GET'])
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


@user_autopublish_bp.route('/dashboard/autopublish/<string:object_id>', methods=['GET'])
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


@user_autopublish_bp.route('/dashboard/autopublish/<string:object_id>/chats', methods=['GET'])
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


@user_autopublish_bp.route('/dashboard/autopublish', methods=['POST'])
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
        
        # Если передана пустая конфигурация с accounts: [], это означает переключение на режим "Бот"
        # В этом случае сохраняем аккаунты с чатами - так при переключении обратно все будет на месте
        if accounts_list == [] and not accounts_config.get('publication_format'):
            old_config = cfg.accounts_config_json
            if isinstance(old_config, dict):
                # Сохраняем всю старую конфигурацию полностью (формат публикации, аккаунты И чаты)
                # Чаты не будут использоваться в режиме "Бот" (не создаются очереди), но останутся в конфигурации
                # При переключении обратно пользователь увидит все как было
                cfg.accounts_config_json = old_config.copy()
            else:
                cfg.accounts_config_json = None
        # Сохраняем конфигурацию если есть валидные аккаунты или если есть только формат публикации
        elif has_valid_accounts or accounts_config.get('publication_format'):
            cfg.accounts_config_json = accounts_config
        elif accounts_list and len(accounts_list) > 0:
            # Если есть аккаунты, но нет выбранных чатов, очищаем конфигурацию аккаунтов
            # Но сохраняем формат публикации, если он есть
            if accounts_config.get('publication_format'):
                cfg.accounts_config_json = {'publication_format': accounts_config.get('publication_format'), 'accounts': []}
            else:
                # Сохраняем список аккаунтов без чатов, но с форматом из старой конфигурации
                old_config = cfg.accounts_config_json
                if isinstance(old_config, dict) and old_config.get('publication_format'):
                    cfg.accounts_config_json = {
                        'publication_format': old_config.get('publication_format'),
                        'accounts': []
                    }
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
                        from app.utils.time_utils import get_next_allowed_time_msk, msk_to_utc, get_moscow_time, is_within_publish_hours
                        now_msk = get_moscow_time()
                        
                        # Если текущее время в пределах разрешенного диапазона - публикуем сразу
                        if is_within_publish_hours(now_msk):
                            scheduled_time_msk = now_msk
                        else:
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
                                if not chat or chat.owner_type != 'user':
                                    continue
                                
                                # Проверяем привязку чата к аккаунту:
                                # 1. Legacy связь через owner_account_id
                                # 2. Новая связь через TelegramAccountChat
                                from app.models.telegram_account_chat import TelegramAccountChat
                                
                                legacy_check = chat.owner_account_id == account_id
                                new_check = db.session.query(TelegramAccountChat).filter_by(
                                    account_id=account_id,
                                    chat_id=chat_id
                                ).first() is not None
                                
                                if legacy_check or new_check:
                                    # Проверяем, нет ли уже такой очереди в AccountPublicationQueue
                                    existing = AccountPublicationQueue.query.filter_by(
                                        object_id=object_id,
                                        chat_id=chat_id,
                                        account_id=account_id,
                                        status='pending'
                                    ).first()
                                    if not existing:
                                        # Получаем время для публикации (8:00-22:00 МСК)
                                        from app.utils.time_utils import get_next_allowed_time_msk, msk_to_utc, is_within_publish_hours
                                        from bot.utils import get_moscow_time
                                        now_msk = get_moscow_time()
                                        
                                        # Если текущее время в пределах разрешенного диапазона - публикуем сразу
                                        if is_within_publish_hours(now_msk):
                                            scheduled_time_msk = now_msk
                                        else:
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
            
            # Запускаем обработку очередей, если есть задачи, готовые к публикации
            from workers.tasks import process_account_autopublish, process_autopublish
            process_account_autopublish.delay()
            process_autopublish.delay()  # Для бота тоже
            
        return jsonify({'success': True, 'config': cfg.to_dict()})
    except Exception as e:
        db.session.rollback()
        log_error(e, 'autopublish_config_save_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({'error': str(e)}), 500


@user_autopublish_bp.route('/dashboard/autopublish/<string:object_id>', methods=['PUT'])
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
        
        # Если передана пустая конфигурация с accounts: [], это означает переключение на режим "Бот"
        # В этом случае сохраняем аккаунты с пустыми chat_ids - так фронтенд покажет аккаунты как выбранные
        # Чаты сохраняются в старой конфигурации, но не используются (не создаются очереди)
        # При переключении обратно пользователь увидит аккаунты и сможет быстро выбрать чаты
        if isinstance(accounts_config, dict) and accounts_config.get('accounts') == []:
            old_config = cfg.accounts_config_json
            if isinstance(old_config, dict):
                # Восстанавливаем аккаунты с пустыми chat_ids, но сохраняем всю старую конфигурацию
                restored_config = {
                    'publication_format': old_config.get('publication_format', 'default'),
                    'accounts': []
                }
                # Восстанавливаем аккаунты с пустыми chat_ids
                if old_config.get('accounts'):
                    for old_acc in old_config.get('accounts', []):
                        if isinstance(old_acc, dict) and old_acc.get('account_id'):
                            restored_config['accounts'].append({
                                'account_id': old_acc.get('account_id'),
                                'chat_ids': old_acc.get('chat_ids', [])  # Сохраняем чаты для быстрого восстановления
                            })
                accounts_config = restored_config
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
                        from app.utils.time_utils import get_next_allowed_time_msk, msk_to_utc, get_moscow_time, is_within_publish_hours
                        now_msk = get_moscow_time()
                        
                        # Если текущее время в пределах разрешенного диапазона - публикуем сразу
                        if is_within_publish_hours(now_msk):
                            scheduled_time_msk = now_msk
                        else:
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
                                if not chat or chat.owner_type != 'user':
                                    continue
                                
                                # Проверяем привязку чата к аккаунту:
                                # 1. Legacy связь через owner_account_id
                                # 2. Новая связь через TelegramAccountChat
                                from app.models.telegram_account_chat import TelegramAccountChat
                                
                                legacy_check = chat.owner_account_id == account_id
                                new_check = db.session.query(TelegramAccountChat).filter_by(
                                    account_id=account_id,
                                    chat_id=chat_id
                                ).first() is not None
                                
                                if legacy_check or new_check:
                                    # Проверяем, нет ли уже такой очереди в AccountPublicationQueue
                                    existing = AccountPublicationQueue.query.filter_by(
                                        object_id=object_id,
                                        chat_id=chat_id,
                                        account_id=account_id,
                                        status='pending'
                                    ).first()
                                    if not existing:
                                        # Получаем время для публикации (8:00-22:00 МСК)
                                        from app.utils.time_utils import get_next_allowed_time_msk, msk_to_utc, is_within_publish_hours
                                        from bot.utils import get_moscow_time
                                        now_msk = get_moscow_time()
                                        
                                        # Если текущее время в пределах разрешенного диапазона - публикуем сразу
                                        if is_within_publish_hours(now_msk):
                                            scheduled_time_msk = now_msk
                                        else:
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
            
            # Запускаем обработку очередей, если есть задачи, готовые к публикации
            from workers.tasks import process_account_autopublish, process_autopublish
            process_account_autopublish.delay()
            process_autopublish.delay()  # Для бота тоже
        
        return jsonify({'success': True, 'config': cfg.to_dict()})
    except Exception as e:
        db.session.rollback()
        log_error(e, 'autopublish_config_update_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({'error': str(e)}), 500


@user_autopublish_bp.route('/dashboard/autopublish/<string:object_id>', methods=['DELETE'])
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


