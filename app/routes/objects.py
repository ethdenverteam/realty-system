"""
API роуты для работы с объектами недвижимости
Цель: CRUD операции для объектов, логирование всех действий пользователя
"""
from flask import Blueprint, request, jsonify, current_app, render_template
from app.database import db
from app.models.object import Object
from app.utils.decorators import jwt_required, role_required
from app.utils.logger import log_action, log_error
from sqlalchemy import or_, and_
import logging

objects_bp = Blueprint('objects', __name__)
logger = logging.getLogger(__name__)


@objects_bp.route('/create', methods=['GET'])
@jwt_required
def create_object_page(current_user):
    """Show object creation page"""
    return render_template('create_object.html')


@objects_bp.route('/list', methods=['GET'])
@jwt_required
def list_objects_page(current_user):
    """Show objects list page"""
    return render_template('objects_list.html')


@objects_bp.route('/', methods=['GET'])
@jwt_required
def list_objects(current_user):
    """
    Получение списка объектов недвижимости пользователя
    Логика: фильтрация, поиск, сортировка, пагинация - все действия логируются
    """
    try:
        # Получаем параметры запроса
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        rooms_type = request.args.get('rooms_type')
        search = request.args.get('search')
        sort_by = request.args.get('sort_by', 'creation_date')
        sort_order = request.args.get('sort_order', 'desc')
        
        logger.info(f"User {current_user.user_id} requested objects list: page={page}, filters={{status={status}, rooms={rooms_type}, search={search}}}")
        
        # Строим запрос с фильтром по пользователю
        query = Object.query.filter_by(user_id=current_user.user_id)
        
        # Применяем фильтры
        if status:
            query = query.filter(Object.status == status)
        
        if rooms_type:
            query = query.filter(Object.rooms_type == rooms_type)
        
        # Поиск по ID, адресу или комментарию
        if search:
            search_filter = or_(
                Object.object_id.ilike(f'%{search}%'),
                Object.address.ilike(f'%{search}%'),
                Object.comment.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        # Применяем сортировку
        if sort_by == 'price':
            order_by = Object.price.desc() if sort_order == 'desc' else Object.price.asc()
        elif sort_by == 'publication_date':
            order_by = Object.publication_date.desc() if sort_order == 'desc' else Object.publication_date.asc()
        else:  # creation_date (по умолчанию)
            order_by = Object.creation_date.desc() if sort_order == 'desc' else Object.creation_date.asc()
        
        query = query.order_by(order_by)
        
        # Пагинация
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Логируем успешное получение списка
        log_action(
            action='objects_list_viewed',
            user_id=current_user.user_id,
            details={
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'filters': {
                    'status': status,
                    'rooms_type': rooms_type,
                    'search': search,
                    'sort_by': sort_by,
                    'sort_order': sort_order
                }
            }
        )
        
        return jsonify({
            'objects': [obj.to_dict() for obj in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
    except Exception as e:
        logger.error(f"Error listing objects for user {current_user.user_id}: {e}", exc_info=True)
        log_error(
            error=e,
            action='objects_list_viewed',
            user_id=current_user.user_id
        )
        return jsonify({'error': 'Failed to retrieve objects'}), 500


@objects_bp.route('/<object_id>', methods=['GET'])
@jwt_required
def get_object(object_id, current_user):
    """
    Получение одного объекта недвижимости
    Логика: проверка прав доступа (только свои объекты), логирование просмотра
    """
    try:
        logger.info(f"User {current_user.user_id} requested object {object_id}")
        
        obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
        
        if not obj:
            logger.warning(f"Object {object_id} not found for user {current_user.user_id}")
            log_action(
                action='object_view_failed',
                user_id=current_user.user_id,
                details={'object_id': object_id, 'reason': 'not_found'}
            )
            return jsonify({'error': 'Object not found'}), 404
        
        # Логируем успешный просмотр объекта
        log_action(
            action='object_viewed',
            user_id=current_user.user_id,
            details={'object_id': object_id, 'status': obj.status}
        )
        
        return jsonify(obj.to_dict())
    except Exception as e:
        logger.error(f"Error getting object {object_id} for user {current_user.user_id}: {e}", exc_info=True)
        log_error(
            error=e,
            action='object_viewed',
            user_id=current_user.user_id,
            details={'object_id': object_id}
        )
        return jsonify({'error': 'Failed to retrieve object'}), 500


@objects_bp.route('/', methods=['POST'])
@jwt_required
def create_object(current_user):
    """
    Создание нового объекта недвижимости
    Логика: поддержка multipart/form-data (загрузка файлов) и JSON, генерация уникального ID, сохранение в БД
    Все создания объектов логируются для аудита
    """
    from werkzeug.utils import secure_filename
    import os
    import json
    
    # Check if form data (file upload) or JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Handle form data with file uploads
        rooms_type = request.form.get('rooms_type', '')
        price = float(request.form.get('price', 0))
        area = float(request.form.get('area', 0)) if request.form.get('area') else None
        floor = request.form.get('floor', '')
        comment = request.form.get('comment', '')
        address = request.form.get('address', '')
        residential_complex = request.form.get('residential_complex', '')
        renovation = request.form.get('renovation', '')
        contact_name = request.form.get('contact_name', '')
        phone_number = request.form.get('phone_number', '')
        contact_name_2 = request.form.get('contact_name_2', '')
        phone_number_2 = request.form.get('phone_number_2', '')
        show_username = request.form.get('show_username') == 'true'
        
        # Parse districts
        districts_json_str = request.form.get('districts_json', '[]')
        try:
            districts_json = json.loads(districts_json_str) if districts_json_str else []
            # Убеждаемся, что districts_json это список
            if not isinstance(districts_json, list):
                districts_json = []
        except:
            districts_json = []
        
        # Handle photo upload - только одно фото разрешено
        photos_json = []
        if 'photo_0' in request.files:
            file = request.files['photo_0']
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Create unique filename
                from datetime import datetime
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
                filename = f"{timestamp}_{filename}"
                from app.config import Config
                filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                file.save(filepath)
                
                # Always store only path to file on server
                # Bot will load file from server when needed
                photos_json.append(f"uploads/{filename}")
    else:
        # Handle JSON data
        data = request.get_json()
        rooms_type = data.get('rooms_type', '')
        price = float(data.get('price', 0))
        area = data.get('area')
        floor = data.get('floor', '')
        comment = data.get('comment', '')
        address = data.get('address', '')
        residential_complex = data.get('residential_complex', '')
        renovation = data.get('renovation', '')
        contact_name = data.get('contact_name', '')
        phone_number = data.get('phone_number', '')
        contact_name_2 = data.get('contact_name_2', '')
        phone_number_2 = data.get('phone_number_2', '')
        show_username = data.get('show_username', False)
        districts_json = data.get('districts_json', [])
        # Убеждаемся, что districts_json это список
        if not isinstance(districts_json, list):
            logger.warning(f"districts_json is not a list, got {type(districts_json)}: {districts_json}")
            districts_json = []
        logger.info(f"Creating object with districts_json: {districts_json} (type: {type(districts_json)})")
        photos_json = data.get('photos_json', [])
    
    # Generate object_id (proper logic from bot)
    prefix = current_user.settings_json.get('id_prefix', 'WEB') if current_user.settings_json else 'WEB'
    if not prefix:
        # Generate prefix if not exists
        from bot.utils import generate_next_id_prefix
        prefix = generate_next_id_prefix()
        if not current_user.settings_json:
            current_user.settings_json = {}
        current_user.settings_json['id_prefix'] = prefix
        db.session.commit()
    
    # Get next number for user
    last_obj = Object.query.filter(
        Object.object_id.like(f'{prefix}%')
    ).order_by(Object.object_id.desc()).first()
    
    if last_obj:
        try:
            num = int(last_obj.object_id[len(prefix):]) + 1
        except:
            num = 1
    else:
        num = 1
    
    object_id = f"{prefix}{num:03d}"
    
    # Create object
    obj = Object(
        object_id=object_id,
        user_id=current_user.user_id,
        rooms_type=rooms_type,
        price=price,
        districts_json=districts_json,
        region=None,  # TODO: Extract from districts
        city=None,  # TODO: Extract from districts
        photos_json=photos_json,
        area=area,
        floor=floor,
        address=address,
        residential_complex=residential_complex if residential_complex else None,
        renovation=renovation,
        comment=comment,
        contact_name=contact_name,
        show_username=show_username,
        phone_number=phone_number,
        contact_name_2=contact_name_2 if contact_name_2 else None,
        phone_number_2=phone_number_2 if phone_number_2 else None,
        status='черновик',
        source='web'
    )
    
    try:
        db.session.add(obj)
        db.session.commit()
        
        # Log creation with districts
        log_action(
            action='object_created',
            user_id=current_user.user_id,
            details={
                'object_id': object_id,
                'rooms_type': obj.rooms_type,
                'price': obj.price,
                'districts_json': obj.districts_json,
                'status': obj.status,
                'source': 'web'
            }
        )
        
        # Verify districts were saved
        logger.info(f"Object {object_id} created with districts: {obj.districts_json}")
        
        return jsonify({
            'success': True,
            'object_id': object_id,
            'object': obj.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        log_error(e, 'object_create_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({'error': str(e)}), 500


@objects_bp.route('/<object_id>', methods=['PUT'])
@jwt_required
def update_object(object_id, current_user):
    """Update object"""
    obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
    
    if not obj:
        return jsonify({'error': 'Object not found'}), 404
    
    data = request.get_json()
    
    # Логируем входящие данные для отладки
    logger.info(f"Object {object_id} update request: districts_json={data.get('districts_json')}, type={type(data.get('districts_json'))}")
    
    # Update fields
    if 'rooms_type' in data:
        obj.rooms_type = data['rooms_type']
    if 'price' in data:
        obj.price = float(data['price'])
    if 'districts_json' in data:
        # Всегда обновляем районы, даже если это пустой список
        districts_json = data['districts_json']
        # Убеждаемся, что это список
        if not isinstance(districts_json, list):
            logger.warning(f"Object {object_id} districts_json is not a list, got {type(districts_json)}: {districts_json}")
            districts_json = []
        old_districts = obj.districts_json
        obj.districts_json = districts_json
        logger.info(f"Object {object_id} districts updated: {old_districts} -> {districts_json}")
    if 'photos_json' in data:
        # Ограничиваем до одного фото
        photos_data = data['photos_json']
        if isinstance(photos_data, list) and len(photos_data) > 0:
            obj.photos_json = [photos_data[0]]  # Берем только первое фото
        else:
            obj.photos_json = []
    if 'area' in data:
        obj.area = data['area']
    if 'floor' in data:
        obj.floor = data['floor']
    if 'address' in data:
        obj.address = data['address']
    if 'residential_complex' in data:
        obj.residential_complex = data['residential_complex'] if data['residential_complex'] else None
    if 'renovation' in data:
        obj.renovation = data['renovation']
    if 'comment' in data:
        obj.comment = data['comment']
    if 'contact_name' in data:
        obj.contact_name = data['contact_name']
    if 'show_username' in data:
        obj.show_username = data['show_username']
    if 'phone_number' in data:
        obj.phone_number = data['phone_number']
    if 'contact_name_2' in data:
        obj.contact_name_2 = data['contact_name_2']
    if 'phone_number_2' in data:
        obj.phone_number_2 = data['phone_number_2']
    if 'status' in data:
        obj.status = data['status']
    
    try:
        # Store old status for logging
        old_status = obj.status
        db.session.commit()
        
        # Log update
        log_action(
            action='object_updated',
            user_id=current_user.user_id,
            details={
                'object_id': object_id,
                'updated_fields': list(data.keys()),
                'old_status': old_status if 'status' in data else None,
                'new_status': obj.status if 'status' in data else None
            }
        )
        
        return jsonify(obj.to_dict())
    except Exception as e:
        db.session.rollback()
        log_error(e, 'object_update_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({'error': str(e)}), 500


@objects_bp.route('/<object_id>', methods=['DELETE'])
@jwt_required
def delete_object(object_id, current_user):
    """Delete object"""
    from app.models.publication_history import PublicationHistory
    
    obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
    
    if not obj:
        return jsonify({'error': 'Object not found'}), 404
    
    try:
        # Store object info for logging
        object_info = {
            'object_id': object_id,
            'rooms_type': obj.rooms_type,
            'price': obj.price,
            'status': obj.status
        }
        
        # First, delete all related publication_history records
        # This prevents NOT NULL constraint violation
        PublicationHistory.query.filter_by(object_id=object_id).delete()
        
        # Now delete the object
        db.session.delete(obj)
        db.session.commit()
        
        # Log deletion
        log_action(
            action='object_deleted',
            user_id=current_user.user_id,
            details=object_info
        )
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        log_error(e, 'object_delete_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({'error': str(e)}), 500


@objects_bp.route('/publish-via-account', methods=['POST'])
@jwt_required
def publish_object_via_account(current_user):
    """Publish object via user Telegram account"""
    from datetime import datetime, timedelta
    import logging
    from app.models.telegram_account import TelegramAccount
    from app.models.chat import Chat
    from app.models.telegram_account_chat import TelegramAccountChat
    from app.models.publication_history import PublicationHistory
    from app.utils.telethon_client import send_object_message, run_async
    from app.utils.rate_limiter import get_rate_limit_status
    from bot.utils import format_publication_text
    from bot.models import User as BotUser, Object as BotObject
    from bot.database import get_db as get_bot_db
    
    data = request.get_json()
    object_id = data.get('object_id')
    account_id = data.get('account_id')
    chat_id = data.get('chat_id')
    
    if not object_id or not account_id or not chat_id:
        return jsonify({'error': 'object_id, account_id, and chat_id are required'}), 400
    
    # Get account
    account = TelegramAccount.query.get(account_id)
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    # Check ownership
    if current_user.web_role != 'admin' and account.owner_id != current_user.user_id:
        return jsonify({'error': 'Access denied'}), 403
    
    # Get chat
    chat = Chat.query.get(chat_id)
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404
    
    # Check chat is linked to this account (many-to-many связь)
    link = TelegramAccountChat.query.filter_by(
        account_id=account_id,
        chat_id=chat.chat_id
    ).first()
    if not link:
        return jsonify({'error': 'Chat does not belong to this account'}), 400
    
    # Get object
    obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
    if not obj:
        return jsonify({'error': 'Object not found'}), 404
    
    # Check rate limits
    rate_status = get_rate_limit_status(account.phone)
    if not rate_status['can_send']:
        wait_seconds = rate_status['wait_seconds']
        minutes = int(wait_seconds // 60)
        seconds = int(wait_seconds % 60)
        if minutes > 0:
            wait_msg = f"{minutes} мин {seconds} сек"
        else:
            wait_msg = f"{seconds} сек"
        
        reason = "В эту минуту уже было отправлено сообщение" if wait_seconds < 60 else "Превышен часовой лимит (60 сообщений в час)"
        
        return jsonify({
            'error': 'Превышен лимит отправки сообщений',
            'details': f'{reason}. Подождите {wait_msg} перед следующей отправкой.',
            'wait_seconds': wait_seconds,
            'wait_message': wait_msg,
            'reason': reason,
            'next_available': rate_status['next_available']
        }), 429
    
    # Check if object was published to this chat within last 24 hours
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
            return jsonify({
                'error': 'Object was already published to this chat within 24 hours'
            }), 400
    
    try:
        # Get bot user and object for formatting
        bot_user = None
        bot_db = get_bot_db()
        try:
            if hasattr(current_user, 'telegram_id') and current_user.telegram_id:
                bot_user = bot_db.query(BotUser).filter_by(telegram_id=int(current_user.telegram_id)).first()
        finally:
            bot_db.close()
        
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
                bot_db.add(bot_obj)
                bot_db.commit()
        finally:
            bot_db.close()
        
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
        publication_text = format_publication_text(bot_obj, bot_user, is_preview=False, publication_format=publication_format)
        
        # Send message via telethon
        logger.info(f"Attempting to publish object {object_id} via account {account_id} to chat {chat_id} (telegram_chat_id: {chat.telegram_chat_id})")
        try:
            success, error_msg, message_id = run_async(
                send_object_message(
                    account.phone,
                    chat.telegram_chat_id,
                    publication_text,
                    obj.photos_json or []
                )
            )
        except Exception as send_error:
            logger.error(f"Exception in run_async(send_object_message): {send_error}", exc_info=True)
            account.last_error = str(send_error)
            account.last_used = datetime.utcnow()
            db.session.commit()
            return jsonify({'error': f'Ошибка при отправке сообщения: {str(send_error)}'}), 500
        
        if not success:
            logger.error(f"Failed to publish object {object_id} via account {account_id}: {error_msg}")
            account.last_error = error_msg
            account.last_used = datetime.utcnow()
            db.session.commit()
            return jsonify({'error': error_msg or 'Ошибка публикации объекта'}), 500
        
        # Update chat statistics
        chat.total_publications = (chat.total_publications or 0) + 1
        chat.last_publication = datetime.utcnow()
        
        # Create publication history
        history = PublicationHistory(
            object_id=object_id,
            chat_id=chat_id,
            account_id=account_id,
            published_at=datetime.utcnow(),
            message_id=str(message_id) if message_id else None,
            deleted=False
        )
        db.session.add(history)
        
        # Update object status
        obj.status = "опубликовано"
        obj.publication_date = datetime.utcnow()
        
        # Update account
        account.last_used = datetime.utcnow()
        account.last_error = None
        
        db.session.commit()
        
        # Log action
        log_action(
            action='web_object_published_via_account',
            user_id=current_user.user_id,
            details={
                'object_id': object_id,
                'account_id': account_id,
                'chat_id': chat_id,
                'message_id': message_id
            }
        )
        
        return jsonify({
            'success': True,
            'message_id': message_id,
            'message': 'Object published successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error publishing object via account: {e}", exc_info=True)
        log_error(e, 'web_object_publish_via_account_failed', current_user.user_id, {
            'object_id': object_id,
            'account_id': account_id,
            'chat_id': chat_id
        })
        return jsonify({'error': str(e)}), 500


@objects_bp.route('/publish', methods=['POST'])
@jwt_required
def publish_object_via_bot(current_user):
    """Publish object via bot"""
    import requests
    import time
    from bot.config import BOT_TOKEN
    from app.models.chat import Chat
    from app.models.publication_history import PublicationHistory
    from bot.utils import (
        format_publication_text, get_districts_config, get_price_ranges,
        get_moscow_time, format_moscow_datetime
    )
    from bot.models import User as BotUser, Object as BotObject
    from bot.database import get_db as get_bot_db
    
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
                bot_db.add(bot_obj)
                bot_db.commit()
        finally:
            bot_db.close()
        
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
        publication_text = format_publication_text(bot_obj, bot_user, is_preview=False, publication_format=publication_format)
        
        # Get target chats (reuse logic from bot)
        target_chats = []
        bot_db = get_bot_db()
        try:
            chats = bot_db.query(Chat).filter_by(owner_type='bot', is_active=True).all()
            
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
                
                if matches and chat.chat_id not in target_chats:
                    target_chats.append(chat.chat_id)
        finally:
            bot_db.close()
        
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
                    recent_pub = PublicationHistory.query.filter(
                        PublicationHistory.object_id == object_id,
                        PublicationHistory.chat_id == chat_id,
                        PublicationHistory.published_at >= yesterday,
                        PublicationHistory.deleted == False
                    ).first()
                    
                    if recent_pub:
                        continue
                
                telegram_chat_id = chat.telegram_chat_id
                
                # Send message - всегда отправляем фото если оно есть
                photos_json = obj.photos_json or []
                
                if photos_json and len(photos_json) > 0:
                    # Берем первое фото (только одно фото разрешено)
                    photo_path = photos_json[0]
                    if isinstance(photo_path, dict):
                        photo_path = photo_path.get('file_id') or photo_path.get('path', '')
                    
                    # Если это путь к файлу на диске, отправляем через sendPhoto
                    if isinstance(photo_path, str) and (photo_path.startswith('uploads/') or '/' in photo_path):
                        from app.config import Config
                        import os
                        # Используем Config.UPLOAD_FOLDER напрямую
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
                            send_url = f'{url}/sendPhoto'
                            with open(full_path, 'rb') as photo_file:
                                files = {'photo': photo_file}
                                payload = {
                                    'chat_id': telegram_chat_id,
                                    'caption': publication_text,
                                    'parse_mode': 'HTML'
                                }
                                response = requests.post(send_url, files=files, data=payload, timeout=30)
                        else:
                            logger.warning(f"Photo file not found: {full_path}, sending text only")
                            send_url = f'{url}/sendMessage'
                            payload = {
                                'chat_id': telegram_chat_id,
                                'text': publication_text,
                                'parse_mode': 'HTML'
                            }
                            response = requests.post(send_url, json=payload, timeout=10)
                    else:
                        # Если это не путь к файлу, отправляем только текст
                        send_url = f'{url}/sendMessage'
                        payload = {
                            'chat_id': telegram_chat_id,
                            'text': publication_text,
                            'parse_mode': 'HTML'
                        }
                        response = requests.post(send_url, json=payload, timeout=10)
                else:
                    # Если фото нет - отправляем только текст
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
