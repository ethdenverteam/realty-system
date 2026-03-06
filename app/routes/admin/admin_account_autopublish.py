"""
Admin account autopublish monitoring routes
Логика: мониторинг автопубликации от имени аккаунтов, управление rate limit, тестовая публикация
"""
from flask import Blueprint, request, jsonify, render_template
from app.database import db
from app.models.user import User
from app.models.object import Object
from app.models.chat import Chat
from app.models.telegram_account_chat import TelegramAccountChat
from app.models.chat_group import ChatGroup
from app.models.action_log import ActionLog
from app.utils.decorators import jwt_required, role_required
from app.utils.logger import log_action, log_error
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import logging

admin_account_autopublish_bp = Blueprint('admin_account_autopublish', __name__)
logger = logging.getLogger(__name__)

@admin_account_autopublish_bp.route('/dashboard/account-autopublish/monitor', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_account_autopublish_monitor(current_user):
    """Данные мониторинга автопубликации от имени аккаунтов (для веб-страницы админа)."""
    from app.models.account_publication_queue import AccountPublicationQueue
    from app.models.telegram_account import TelegramAccount
    from app.models.autopublish_config import AutopublishConfig
    from app.models.publication_history import PublicationHistory
    from app.models.system_setting import SystemSetting

    try:
        now = datetime.utcnow()
        threshold_minutes = request.args.get('threshold_minutes', 5, type=int) or 5
        stuck_threshold = now - timedelta(minutes=threshold_minutes)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        active_accounts = TelegramAccount.query.filter_by(is_active=True).order_by(TelegramAccount.account_id.asc()).all()

        # Глобальный переключатель лимита по аккаунтам (используется в app.utils.rate_limiter)
        rate_limit_setting = SystemSetting.query.filter_by(key='account_rate_limit').first()
        rate_limit_enabled = True
        if rate_limit_setting and isinstance(rate_limit_setting.value_json, dict):
            rate_limit_enabled = bool(rate_limit_setting.value_json.get('enabled', True))

        account_rows = []
        for acc in active_accounts:
            today_pubs = db.session.query(
                func.count(PublicationHistory.history_id)
            ).filter(
                PublicationHistory.account_id == acc.account_id,
                PublicationHistory.published_at >= today_start,
                PublicationHistory.deleted == False
            ).scalar() or 0

            pending_count = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
                AccountPublicationQueue.account_id == acc.account_id,
                AccountPublicationQueue.status == 'pending',
            ).scalar() or 0
            processing_count = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
                AccountPublicationQueue.account_id == acc.account_id,
                AccountPublicationQueue.status == 'processing',
            ).scalar() or 0
            failed_count = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
                AccountPublicationQueue.account_id == acc.account_id,
                AccountPublicationQueue.status == 'failed',
            ).scalar() or 0
            completed_count = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
                AccountPublicationQueue.account_id == acc.account_id,
                AccountPublicationQueue.status == 'completed',
            ).scalar() or 0
            flood_wait_count = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
                AccountPublicationQueue.account_id == acc.account_id,
                AccountPublicationQueue.status == 'flood_wait',
            ).scalar() or 0

            next_pending = db.session.query(AccountPublicationQueue).filter(
                AccountPublicationQueue.account_id == acc.account_id,
                AccountPublicationQueue.status == 'pending',
            ).order_by(AccountPublicationQueue.scheduled_time.asc()).first()

            account_rows.append({
                'account_id': acc.account_id,
                'phone': acc.phone,
                'mode': acc.mode,
                'daily_limit': acc.daily_limit,
                'today_publications': int(today_pubs),
                'last_used': acc.last_used.isoformat() if acc.last_used else None,
                'last_error': acc.last_error,
                'queue': {
                    'pending': int(pending_count),
                    'processing': int(processing_count),
                    'failed': int(failed_count),
                    'completed': int(completed_count),
                    'flood_wait': int(flood_wait_count),
                },
                'next_pending': {
                    'queue_id': next_pending.queue_id,
                    'scheduled_time': next_pending.scheduled_time.isoformat() if next_pending.scheduled_time else None,
                } if next_pending else None,
            })

        total_queues = db.session.query(AccountPublicationQueue).count()
        pending_queues = db.session.query(AccountPublicationQueue).filter_by(status='pending').count()
        processing_queues = db.session.query(AccountPublicationQueue).filter_by(status='processing').count()
        completed_queues = db.session.query(AccountPublicationQueue).filter_by(status='completed').count()
        failed_queues = db.session.query(AccountPublicationQueue).filter_by(status='failed').count()
        flood_wait_queues = db.session.query(AccountPublicationQueue).filter_by(status='flood_wait').count()

        ready_queues = db.session.query(AccountPublicationQueue).filter(
            AccountPublicationQueue.status == 'pending',
            AccountPublicationQueue.scheduled_time <= now
        ).order_by(AccountPublicationQueue.scheduled_time.asc()).limit(20).all()

        stuck_queues = db.session.query(AccountPublicationQueue).filter(
            AccountPublicationQueue.status == 'processing',
            AccountPublicationQueue.started_at < stuck_threshold
        ).order_by(AccountPublicationQueue.started_at.asc()).all()

        enabled_configs = db.session.query(AutopublishConfig).filter_by(enabled=True).count()
        total_configs = db.session.query(AutopublishConfig).count()

        def _queue_payload(q):
            obj = Object.query.get(q.object_id)
            chat = Chat.query.get(q.chat_id)
            account = TelegramAccount.query.get(q.account_id) if q.account_id else None
            return {
                'queue_id': q.queue_id,
                'object_id': q.object_id,
                'object_title': obj.object_id if obj else None,
                'chat_id': q.chat_id,
                'chat_title': chat.title if chat else None,
                'account_id': q.account_id,
                'account_phone': account.phone if account else None,
                'status': q.status,
                'attempts': q.attempts,
                'scheduled_time': q.scheduled_time.isoformat() if q.scheduled_time else None,
                'started_at': q.started_at.isoformat() if q.started_at else None,
                'created_at': q.created_at.isoformat() if q.created_at else None,
                'error_message': q.error_message,
            }

        return jsonify({
            'success': True,
            'now_utc': now.isoformat(),
            'threshold_minutes': threshold_minutes,
            'summary': {
                'active_accounts': len(active_accounts),
                'total_queues': total_queues,
                'pending': pending_queues,
                'processing': processing_queues,
                'completed': completed_queues,
                'failed': failed_queues,
                'flood_wait': flood_wait_queues,
                'ready_count': len(ready_queues),
                'stuck_count': len(stuck_queues),
                'enabled_configs': enabled_configs,
                'total_configs': total_configs,
                'rate_limit_enabled': rate_limit_enabled,
            },
            'rate_limit_enabled': rate_limit_enabled,
            'accounts': account_rows,
            'ready_queues': [_queue_payload(q) for q in ready_queues],
            'stuck_queues': [_queue_payload(q) for q in stuck_queues],
        }), 200

    except Exception as e:
        logger.error(f"Error in account autopublish monitor: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_account_autopublish_bp.route('/dashboard/account-autopublish/rate-limit', methods=['POST'])
@jwt_required
@role_required('admin')
def admin_account_autopublish_rate_limit_toggle(current_user):
    """
    Глобальный переключатель лимита отправки сообщений с Telegram-аккаунтов.

    Источник: SystemSetting.key='account_rate_limit', value_json={'enabled': bool}.
    Используется во всех местах, где вызывается get_rate_limit_status().
    """
    from app.models.system_setting import SystemSetting

    data = request.get_json(silent=True) or {}
    enabled = bool(data.get('enabled', True))

    try:
        setting = SystemSetting.query.filter_by(key='account_rate_limit').first()
        if not setting:
            setting = SystemSetting(
                key='account_rate_limit',
                value_json={'enabled': enabled},
                description='Глобальный переключатель rate limiter для аккаунтных публикаций (Telethon)',
                updated_at=datetime.utcnow(),
            )
            db.session.add(setting)
        else:
            setting.value_json = {'enabled': enabled}
            setting.updated_at = datetime.utcnow()

        db.session.commit()

        log_action(
            action='admin_toggle_account_rate_limit',
            user_id=current_user.user_id,
            details={'enabled': enabled},
        )

        return jsonify({'success': True, 'enabled': enabled}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling account rate limit: {e}", exc_info=True)
        log_error(e, 'admin_toggle_account_rate_limit_failed', current_user.user_id, {'enabled': enabled})
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_account_autopublish_bp.route('/dashboard/account-autopublish/reset-stuck', methods=['POST'])
@jwt_required
@role_required('admin')
def admin_account_autopublish_reset_stuck(current_user):
    """Сброс застрявших account_publication_queues в pending/failed."""
    from app.models.account_publication_queue import AccountPublicationQueue

    data = request.get_json(silent=True) or {}
    threshold_minutes = int(data.get('threshold_minutes', 5) or 5)
    max_attempts = int(data.get('max_attempts', 3) or 3)

    try:
        now = datetime.utcnow()
        stuck_threshold = now - timedelta(minutes=threshold_minutes)
        stuck_queues = db.session.query(AccountPublicationQueue).filter(
            AccountPublicationQueue.status == 'processing',
            AccountPublicationQueue.started_at < stuck_threshold
        ).all()

        reset_to_pending = 0
        marked_failed = 0
        changed = []

        for q in stuck_queues:
            q.attempts = (q.attempts or 0) + 1
            if q.attempts >= max_attempts:
                q.status = 'failed'
                q.error_message = q.error_message or 'Task timeout - exceeded processing threshold'
                marked_failed += 1
            else:
                q.status = 'pending'
                q.started_at = None
                q.error_message = None
                reset_to_pending += 1

            changed.append({
                'queue_id': q.queue_id,
                'status': q.status,
                'attempts': q.attempts,
                'object_id': q.object_id,
                'account_id': q.account_id,
                'chat_id': q.chat_id,
            })

        db.session.commit()

        log_action(
            action='admin_reset_stuck_account_queues',
            user_id=current_user.user_id,
            details={
                'threshold_minutes': threshold_minutes,
                'max_attempts': max_attempts,
                'total_found': len(stuck_queues),
                'reset_to_pending': reset_to_pending,
                'marked_failed': marked_failed,
            },
        )

        return jsonify({
            'success': True,
            'threshold_minutes': threshold_minutes,
            'max_attempts': max_attempts,
            'total_found': len(stuck_queues),
            'reset_to_pending': reset_to_pending,
            'marked_failed': marked_failed,
            'queues': changed,
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting stuck account queues: {e}", exc_info=True)
        log_error(e, 'admin_reset_stuck_account_queues_failed', current_user.user_id, {
            'threshold_minutes': threshold_minutes,
            'max_attempts': max_attempts
        })
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_account_autopublish_bp.route('/dashboard/test-account-publication/objects', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_test_account_publication_objects(current_user):
    """Get list of all objects for test publication"""
    try:
        objects = Object.query.order_by(Object.creation_date.desc()).limit(1000).all()
        return jsonify([obj.to_dict() for obj in objects])
    except Exception as e:
        logger.error(f"Error getting objects for test publication: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_account_autopublish_bp.route('/dashboard/test-account-publication/accounts', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_test_account_publication_accounts(current_user):
    """Get list of all accounts with their chats for test publication"""
    try:
        from app.models.telegram_account import TelegramAccount
        accounts = TelegramAccount.query.filter_by(is_active=True).all()
        
        result = []
        for account in accounts:
            # Чаты аккаунта через связь many-to-many TelegramAccountChat
            chats = (
                Chat.query
                .join(TelegramAccountChat, TelegramAccountChat.chat_id == Chat.chat_id)
                .filter(
                    TelegramAccountChat.account_id == account.account_id,
                    Chat.is_active == True,
                )
                .all()
            )

            result.append({
                **account.to_dict(),
                'chats': [chat.to_dict() for chat in chats]
            })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting accounts for test publication: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_account_autopublish_bp.route('/dashboard/test-account-publication/publish', methods=['POST'])
@jwt_required
@role_required('admin')
def admin_test_account_publication_publish(current_user):
    """Publish object via account (admin test)"""
    from datetime import datetime
    from app.models.telegram_account import TelegramAccount
    from app.models.publication_history import PublicationHistory
    from app.utils.telethon_client import send_object_message, run_async
    from app.utils.rate_limiter import get_rate_limit_status
    from bot.utils import format_publication_text
    from bot.models import Object as BotObject
    
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
    
    # Get object (admin can access any object)
    obj = Object.query.filter_by(object_id=object_id).first()
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
    
    try:
        # Формируем BotObject в памяти, не обращаясь к базе бота
        bot_obj = BotObject(
            object_id=obj.object_id,
            user_id=obj.user_id,
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
            source='web',
        )
        bot_user = None  # Для тестовой публикации нам достаточно текста объекта
        
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
        logger.info(f"Admin test publication: object {object_id} via account {account_id} to chat {chat_id} (telegram_chat_id: {chat.telegram_chat_id})")
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
        
        # Update account
        account.last_used = datetime.utcnow()
        account.last_error = None
        
        db.session.commit()
        
        # Log action
        log_action(
            action='admin_test_account_publication',
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
        logger.error(f"Error in admin test account publication: {e}", exc_info=True)
        log_error(e, 'admin_test_account_publication_failed', current_user.user_id, {
            'object_id': object_id,
            'account_id': account_id,
            'chat_id': chat_id
        })
        return jsonify({'error': str(e)}), 500


@admin_account_autopublish_bp.route('/dashboard/check-chat-access', methods=['POST'])
@jwt_required
@role_required('admin')
def admin_check_chat_access(current_user):
    """
    Проверка доступности чата для аккаунта.
    Два варианта:
    1. Только проверка validate_chat_peer (без отправки)
    2. Проверка с реальной отправкой тестового сообщения
    """
    from app.models.telegram_account import TelegramAccount
    from app.utils.telethon.telethon_connection import create_client, validate_chat_peer
    from app.utils.telethon_client import run_async, send_test_message
    
    data = request.get_json()
    account_id = data.get('account_id')
    chat_id = data.get('chat_id')
    with_send = data.get('with_send', False)  # Если True - отправляем тестовое сообщение
    
    if not account_id or not chat_id:
        return jsonify({'error': 'account_id and chat_id are required'}), 400
    
    # Get account
    account = TelegramAccount.query.get(account_id)
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    # Get chat
    chat = Chat.query.get(chat_id)
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404
    
    try:
        client = None
        try:
            # Создаём клиент и подключаемся
            client = run_async(create_client(account.phone))
            run_async(client.connect())
            
            # Проверяем авторизацию
            is_authorized = run_async(client.is_user_authorized())
            if not is_authorized:
                return jsonify({
                    'success': False,
                    'error': 'Account not authorized. Please reconnect the account.',
                    'check_type': 'validation_only' if not with_send else 'validation_with_send',
                }), 400
            
            # Проверка validate_chat_peer
            telegram_chat_id = int(chat.telegram_chat_id)
            is_valid_peer = run_async(validate_chat_peer(client, telegram_chat_id))
            
            result = {
                'success': True,
                'account_id': account_id,
                'account_phone': account.phone,
                'chat_id': chat_id,
                'chat_title': chat.title,
                'telegram_chat_id': telegram_chat_id,
                'check_type': 'validation_only' if not with_send else 'validation_with_send',
                'validation_result': {
                    'is_valid_peer': is_valid_peer,
                    'message': 'Чат доступен для аккаунта' if is_valid_peer else 'Чат недоступен для аккаунта (validate_chat_peer вернул False)',
                },
            }
            
            # Если запрошена проверка с отправкой
            if with_send:
                try:
                    send_success, send_error, message_id = run_async(
                        send_test_message(account.phone, str(telegram_chat_id), "Тестовое сообщение для проверки доступа")
                    )
                    result['send_result'] = {
                        'success': send_success,
                        'message_id': message_id,
                        'error': send_error,
                        'message': 'Сообщение успешно отправлено' if send_success else f'Ошибка отправки: {send_error}',
                    }
                    # Обновляем общий результат
                    result['success'] = send_success
                    if not send_success:
                        result['error'] = send_error
                except Exception as send_exc:
                    logger.error(f"Error sending test message in check_chat_access: {send_exc}", exc_info=True)
                    result['send_result'] = {
                        'success': False,
                        'error': str(send_exc),
                        'message': f'Исключение при отправке: {str(send_exc)}',
                    }
                    result['success'] = False
                    result['error'] = str(send_exc)
            else:
                # Если только проверка без отправки - предупреждаем, что это диагностика
                result['note'] = 'Это только диагностическая проверка. Для реальной проверки используйте вариант с отправкой.'
            
            # Логируем действие
            log_action(
                action='admin_check_chat_access',
                user_id=current_user.user_id,
                details={
                    'account_id': account_id,
                    'chat_id': chat_id,
                    'with_send': with_send,
                    'is_valid_peer': is_valid_peer,
                    'send_success': result.get('send_result', {}).get('success') if with_send else None,
                }
            )
            
            return jsonify(result), 200
            
        finally:
            if client:
                try:
                    run_async(client.disconnect())
                except Exception as disc_err:
                    logger.warning(f"Error disconnecting client in check_chat_access: {disc_err}")
                    
    except Exception as e:
        logger.error(f"Error in admin check chat access: {e}", exc_info=True)
        log_error(e, 'admin_check_chat_access_failed', current_user.user_id, {
            'account_id': account_id,
            'chat_id': chat_id,
            'with_send': with_send,
        })
        return jsonify({
            'success': False,
            'error': str(e),
            'check_type': 'validation_only' if not with_send else 'validation_with_send',
        }), 500
