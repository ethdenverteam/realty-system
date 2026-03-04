"""
Admin publication queues monitoring routes
Логика: мониторинг очередей публикаций (PublicationQueue и AccountPublicationQueue)
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.publication_queue import PublicationQueue
from app.models.account_publication_queue import AccountPublicationQueue
from app.models.object import Object
from app.models.chat import Chat
from app.models.telegram_account import TelegramAccount
from app.models.user import User
from app.utils.decorators import jwt_required, role_required
from sqlalchemy import desc
import logging

admin_publication_queues_bp = Blueprint('admin_publication_queues', __name__)
logger = logging.getLogger(__name__)


def _format_bot_queue(queue):
    """Форматирует очередь бота для ответа"""
    obj = Object.query.get(queue.object_id)
    chat = Chat.query.get(queue.chat_id)
    account = TelegramAccount.query.get(queue.account_id) if queue.account_id else None
    
    queue_dict = queue.to_dict()
    queue_dict['queue_type'] = 'bot'
    queue_dict['object'] = {
        'object_id': obj.object_id if obj else None,
        'rooms_type': obj.rooms_type if obj else None,
        'price': obj.price if obj else None,
        'status': obj.status if obj else None,
    } if obj else None
    queue_dict['chat'] = {
        'chat_id': chat.chat_id if chat else None,
        'title': chat.title if chat else None,
        'telegram_chat_id': chat.telegram_chat_id if chat else None,
    } if chat else None
    queue_dict['account'] = {
        'account_id': account.account_id if account else None,
        'phone': account.phone if account else None,
    } if account else None
    
    if queue.user:
        user = queue.user
        queue_dict['user'] = {
            'user_id': user.user_id,
            'username': user.username,
            'phone': user.phone,
        }
    
    return queue_dict


def _format_account_queue(queue):
    """Форматирует очередь аккаунта для ответа"""
    obj = Object.query.get(queue.object_id)
    chat = Chat.query.get(queue.chat_id)
    account = TelegramAccount.query.get(queue.account_id) if queue.account_id else None
    user = User.query.get(queue.user_id) if queue.user_id else None
    
    queue_dict = queue.to_dict()
    queue_dict['queue_type'] = 'account'
    queue_dict['object'] = {
        'object_id': obj.object_id if obj else None,
        'rooms_type': obj.rooms_type if obj else None,
        'price': obj.price if obj else None,
        'status': obj.status if obj else None,
    } if obj else None
    queue_dict['chat'] = {
        'chat_id': chat.chat_id if chat else None,
        'title': chat.title if chat else None,
        'telegram_chat_id': chat.telegram_chat_id if chat else None,
    } if chat else None
    queue_dict['account'] = {
        'account_id': account.account_id if account else None,
        'phone': account.phone if account else None,
    } if account else None
    queue_dict['user'] = {
        'user_id': user.user_id if user else None,
        'username': user.username if user else None,
        'phone': user.phone if user else None,
    } if user else None
    
    return queue_dict


@admin_publication_queues_bp.route('/dashboard/publication-queues', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_publication_queues_data(current_user):
    """Get publication queues data (both PublicationQueue and AccountPublicationQueue)"""
    queue_type = request.args.get('type', 'all')  # 'bot', 'account', 'all'
    status = request.args.get('status', 'all')  # 'pending', 'processing', 'completed', 'failed', 'all'
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    try:
        queue_data = []
        
        # Получаем задачи из PublicationQueue (бот)
        if queue_type in ('all', 'bot'):
            query = PublicationQueue.query
            
            if queue_type == 'bot':
                query = query.filter_by(type='bot')
            elif queue_type == 'user':
                query = query.filter_by(type='user')
            
            if status != 'all':
                query = query.filter_by(status=status)
            
            query = query.order_by(desc(PublicationQueue.created_at))
            queues = query.offset(offset).limit(limit).all()
            
            for queue in queues:
                queue_data.append(_format_bot_queue(queue))
        
        # Получаем задачи из AccountPublicationQueue (аккаунты)
        if queue_type in ('all', 'account'):
            query = AccountPublicationQueue.query
            
            if status != 'all':
                query = query.filter_by(status=status)
            
            query = query.order_by(desc(AccountPublicationQueue.created_at))
            account_queues = query.offset(offset).limit(limit).all()
            
            for queue in account_queues:
                queue_data.append(_format_account_queue(queue))
        
        # Сортируем все очереди по created_at desc
        queue_data.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Применяем пагинацию к объединенному списку
        total = len(queue_data)
        queue_data = queue_data[offset:offset+limit]
        
        return jsonify({
            'success': True,
            'queues': queue_data,
            'total': total,
            'offset': offset,
            'limit': limit
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting publication queues: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

