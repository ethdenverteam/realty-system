"""
Ручная публикация через Telegram аккаунты пользователей
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.account_publication_queue import AccountPublicationQueue
from app.models.object import Object
from app.models.telegram_account import TelegramAccount
from app.models.chat import Chat
from app.utils.decorators import jwt_required
from app.utils.logger import log_action, log_error
from app.utils.duplicate_checker import check_duplicate_publication
from app.utils.rate_limiter import get_rate_limit_status
from app.utils.account_publication_utils import calculate_scheduled_times_for_account
from app.utils.time_utils import get_moscow_time, msk_to_utc
from datetime import datetime, timedelta
import random
import logging

account_publications_bp = Blueprint('account_publications', __name__)
logger = logging.getLogger(__name__)


@account_publications_bp.route('/manual', methods=['POST'])
@jwt_required
def create_manual_account_publication(current_user):
    """
    Ручная публикация объекта через Telegram аккаунт пользователя
    
    Логика:
    1. Проверяет rate limiter - если не готов, откладывает на 30 минут + джиттер
    2. Проверяет дубликаты через унифицированную утилиту
    3. Распределяет задачи согласно интервалу аккаунта
    4. Если аккаунт готов - первое сообщение отправляется сейчас
    """
    data = request.get_json()
    
    object_id = data.get('object_id')
    account_id = data.get('account_id')
    chat_ids = data.get('chat_ids', [])
    
    if not object_id or not account_id:
        return jsonify({'error': 'object_id and account_id are required'}), 400
    
    if not chat_ids:
        return jsonify({'error': 'chat_ids are required'}), 400
    
    # Проверяем, что объект принадлежит пользователю
    obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
    if not obj:
        return jsonify({'error': 'Object not found'}), 404
    
    # Проверяем, что аккаунт принадлежит пользователю и активен
    account = TelegramAccount.query.filter_by(
        account_id=account_id,
        owner_id=current_user.user_id,
        is_active=True
    ).first()
    
    if not account:
        return jsonify({'error': 'Account not found or inactive'}), 404
    
    # Проверяем чаты - они должны принадлежать этому аккаунту
    chats = Chat.query.filter(
        Chat.chat_id.in_(chat_ids),
        Chat.owner_type == 'user',
        Chat.owner_account_id == account_id,
        Chat.is_active == True
    ).all()
    
    if len(chats) != len(chat_ids):
        return jsonify({'error': 'Some chats not found or not accessible'}), 404
    
    # Проверяем rate limiter
    rate_status = get_rate_limit_status(account.phone)
    now = datetime.utcnow()
    
    # Если rate limit - откладываем на 30 минут + джиттер
    if not rate_status['can_send']:
        jitter_seconds = random.randint(1, 99)
        delay_minutes = 30
        first_scheduled_time = now + timedelta(minutes=delay_minutes, seconds=jitter_seconds)
        logger.info(f"Account {account_id} rate limited, scheduling first message for {first_scheduled_time}")
    else:
        # Если готов - первое сообщение отправляется сейчас
        first_scheduled_time = now
        logger.info(f"Account {account_id} ready, scheduling first message immediately")
    
    # Проверяем дубликаты для каждого чата
    blocked_chats = []
    for chat in chats:
        can_publish, reason = check_duplicate_publication(
            object_id=object_id,
            chat_id=chat.chat_id,
            account_id=account_id,
            publication_type='manual_account',
            user_id=current_user.user_id,
            allow_duplicates_setting=None
        )
        
        if not can_publish:
            blocked_chats.append(chat.chat_id)
    
    if blocked_chats:
        return jsonify({
            'error': 'Object was already published to some chats within 24 hours',
            'blocked_chat_ids': blocked_chats
        }), 400
    
    # Рассчитываем расписание для всех задач
    total_tasks = len(chats)
    now_msk = get_moscow_time()
    
    # Если первое сообщение сейчас - начинаем с текущего времени
    # Иначе начинаем с запланированного времени
    if rate_status['can_send']:
        start_time_msk = now_msk
    else:
        start_time_msk = msk_to_utc(first_scheduled_time)
        # Конвертируем обратно в МСК для расчета расписания
        from app.utils.time_utils import utc_to_msk
        start_time_msk = utc_to_msk(start_time_msk)
    
    # Получаем fix_interval_minutes для режима 'fix'
    fix_interval = getattr(account, 'fix_interval_minutes', None) if account.mode == 'fix' else None
    
    # Рассчитываем расписание
    scheduled_times_msk = calculate_scheduled_times_for_account(
        mode=account.mode,
        total_tasks=total_tasks,
        daily_limit=account.daily_limit,
        start_time_msk=start_time_msk,
        fix_interval=fix_interval
    )
    
    # Создаем задачи в очереди
    queue_ids = []
    try:
        for i, chat in enumerate(chats):
            if i < len(scheduled_times_msk):
                scheduled_time_utc = msk_to_utc(scheduled_times_msk[i])
            else:
                # Если расписание не рассчиталось (превышен лимит) - пропускаем
                continue
            
            queue = AccountPublicationQueue(
                object_id=object_id,
                chat_id=chat.chat_id,
                account_id=account_id,
                user_id=current_user.user_id,
                status='pending',
                scheduled_time=scheduled_time_utc,
                created_at=datetime.utcnow(),
            )
            db.session.add(queue)
            queue_ids.append(queue.queue_id)
        
        db.session.commit()
        
        # Логируем действие
        log_action(
            action='manual_account_publication_queued',
            user_id=current_user.user_id,
            details={
                'object_id': object_id,
                'account_id': account_id,
                'chat_count': len(chats),
                'queue_ids': queue_ids,
                'first_scheduled_time': scheduled_times_msk[0].isoformat() if scheduled_times_msk else None
            }
        )
        
        # Запускаем обработку очереди (если есть задачи, готовые к публикации сейчас)
        if rate_status['can_send'] and queue_ids:
            from workers.tasks import process_account_autopublish
            process_account_autopublish.delay()
        
        return jsonify({
            'success': True,
            'queue_ids': queue_ids,
            'first_scheduled_time': scheduled_times_msk[0].isoformat() if scheduled_times_msk else None,
            'rate_limited': not rate_status['can_send']
        }), 201
        
    except Exception as e:
        db.session.rollback()
        log_error(e, 'manual_account_publication_failed', current_user.user_id, {
            'object_id': object_id,
            'account_id': account_id
        })
        logger.error(f"Error creating manual account publication: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

