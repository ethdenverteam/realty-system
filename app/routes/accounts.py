"""
Telegram accounts routes
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.telegram_account import TelegramAccount
from app.models.chat import Chat
from app.utils.decorators import jwt_required, role_required
from app.utils.logger import log_action, log_error
from app.utils.telethon_client import (
    start_connection, verify_code, verify_2fa, get_chats, 
    send_test_message as telethon_send_test_message, get_session_path, run_async
)
from app.config import Config
from datetime import datetime
import logging
import os
import re

accounts_bp = Blueprint('accounts', __name__)
logger = logging.getLogger(__name__)


@accounts_bp.route('/', methods=['GET'])
@jwt_required
def list_accounts(current_user):
    """Get list of user's Telegram accounts"""
    if current_user.web_role == 'admin':
        accounts = TelegramAccount.query.all()
    else:
        accounts = TelegramAccount.query.filter_by(owner_id=current_user.user_id).all()
    
    return jsonify([acc.to_dict() for acc in accounts])


@accounts_bp.route('/connect/start', methods=['POST'])
@jwt_required
def connect_start(current_user):
    """Start Telegram account connection (step 1: phone number)"""
    data = request.get_json()
    phone = data.get('phone', '').strip()
    
    if not phone:
        return jsonify({'error': 'Phone number is required'}), 400
    
    # Normalize phone number: remove spaces, dashes, parentheses, but keep +
    # Accept any format with country code starting with +
    phone_normalized = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Validate phone format (should start with +)
    if not phone_normalized.startswith('+'):
        return jsonify({'error': 'Phone number must start with + (e.g., +56 9 4095 1404 or +79991234567)'}), 400
    
    # Check minimum length (country code + at least 5 digits)
    if len(phone_normalized) < 7:
        return jsonify({'error': 'Phone number is too short'}), 400
    
    # Use normalized phone for further processing
    phone = phone_normalized
    
    # Log phone number for debugging (especially for international numbers like +56)
    logger.info(f"Processing phone number connection request: original='{data.get('phone', '')}', normalized='{phone}', country_code='{phone[:3] if len(phone) >= 3 else 'unknown'}'")
    
    # Check if account already exists
    existing = TelegramAccount.query.filter_by(phone=phone).first()
    if existing:
        # Check ownership
        if current_user.web_role != 'admin' and existing.owner_id != current_user.user_id:
            return jsonify({'error': 'This phone number is already connected to another account'}), 400
        # Account exists and belongs to user - check if session file exists
        session_path = get_session_path(phone)
        if os.path.exists(session_path):
            return jsonify({
                'error': 'Account already connected',
                'account_id': existing.account_id
            }), 400
    
    try:
        # Start connection
        connection_result = run_async(start_connection(phone))
        
        # Handle both old format (2 values) and new format (3 values)
        if len(connection_result) == 3:
            success, result, warning = connection_result
        else:
            success, result = connection_result
            warning = None
        
        if not success:
            return jsonify({'error': result}), 400
        
        # If already authorized, create account record
        if result is None:
            # Session already exists and authorized
            session_path = get_session_path(phone)
            if not os.path.exists(session_path):
                return jsonify({'error': 'Session file not found'}), 500
            
            # Create or update account
            if existing:
                account = existing
            else:
                account = TelegramAccount(
                    owner_id=current_user.user_id,
                    phone=phone,
                    session_file=session_path,
                    is_active=True
                )
                db.session.add(account)
            
            db.session.commit()
            
            log_action(
                action='account_connected',
                user_id=current_user.user_id,
                details={'account_id': account.account_id, 'phone': phone}
            )
            
            return jsonify({
                'success': True,
                'account_id': account.account_id,
                'message': 'Account already authorized'
            })
        
        # Code sent, return code_hash
        response = {
            'success': True,
            'code_hash': result,
            'message': 'Verification code sent to Telegram'
        }
        if warning:
            response['warning'] = warning
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error starting connection: {e}", exc_info=True)
        log_error(e, 'account_connect_start_failed', current_user.user_id, {'phone': phone})
        return jsonify({'error': f'Connection error: {str(e)}'}), 500


@accounts_bp.route('/connect/verify-code', methods=['POST'])
@jwt_required
def connect_verify_code(current_user):
    """Verify phone code (step 2: verification code)"""
    data = request.get_json()
    phone = data.get('phone', '').strip()
    code = data.get('code', '').strip()
    code_hash = data.get('code_hash', '').strip()
    
    if not phone or not code or not code_hash:
        return jsonify({'error': 'Phone, code, and code_hash are required'}), 400
    
    # Normalize phone number
    phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    try:
        success, error_msg, requires_2fa = run_async(verify_code(phone, code, code_hash))
        
        if not success:
            return jsonify({'error': error_msg}), 400
        
        if requires_2fa:
            # 2FA required
            return jsonify({
                'success': True,
                'requires_2fa': True,
                'message': '2FA password required'
            })
        
        # Successfully connected - create account record
        session_path = get_session_path(phone)
        if not os.path.exists(session_path):
            return jsonify({'error': 'Session file not created'}), 500
        
        # Check if account already exists
        account = TelegramAccount.query.filter_by(phone=phone).first()
        if account:
            # Update existing
            if current_user.web_role != 'admin' and account.owner_id != current_user.user_id:
                return jsonify({'error': 'Access denied'}), 403
            account.session_file = session_path
            account.is_active = True
            account.last_error = None
        else:
            # Create new
            account = TelegramAccount(
                owner_id=current_user.user_id,
                phone=phone,
                session_file=session_path,
                is_active=True
            )
            db.session.add(account)
        
        db.session.commit()
        
        log_action(
            action='account_connected',
            user_id=current_user.user_id,
            details={'account_id': account.account_id, 'phone': phone}
        )
        
        return jsonify({
            'success': True,
            'account_id': account.account_id,
            'requires_2fa': False,
            'message': 'Account connected successfully'
        })
    except Exception as e:
        logger.error(f"Error verifying code: {e}", exc_info=True)
        log_error(e, 'account_verify_code_failed', current_user.user_id, {'phone': phone})
        return jsonify({'error': f'Verification error: {str(e)}'}), 500


@accounts_bp.route('/connect/verify-2fa', methods=['POST'])
@jwt_required
def connect_verify_2fa(current_user):
    """Verify 2FA password (step 3: 2FA code)"""
    data = request.get_json()
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()
    
    if not phone or not password:
        return jsonify({'error': 'Phone and password are required'}), 400
    
    # Normalize phone number
    phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    try:
        success, error_msg = run_async(verify_2fa(phone, password))
        
        if not success:
            return jsonify({'error': error_msg}), 400
        
        # Successfully connected - create account record
        session_path = get_session_path(phone)
        if not os.path.exists(session_path):
            return jsonify({'error': 'Session file not created'}), 500
        
        # Check if account already exists
        account = TelegramAccount.query.filter_by(phone=phone).first()
        if account:
            # Update existing
            if current_user.web_role != 'admin' and account.owner_id != current_user.user_id:
                return jsonify({'error': 'Access denied'}), 403
            account.session_file = session_path
            account.is_active = True
            account.last_error = None
        else:
            # Create new
            account = TelegramAccount(
                owner_id=current_user.user_id,
                phone=phone,
                session_file=session_path,
                is_active=True
            )
            db.session.add(account)
        
        db.session.commit()
        
        log_action(
            action='account_connected',
            user_id=current_user.user_id,
            details={'account_id': account.account_id, 'phone': phone, 'with_2fa': True}
        )
        
        return jsonify({
            'success': True,
            'account_id': account.account_id,
            'message': 'Account connected successfully with 2FA'
        })
    except Exception as e:
        logger.error(f"Error verifying 2FA: {e}", exc_info=True)
        log_error(e, 'account_verify_2fa_failed', current_user.user_id, {'phone': phone})
        return jsonify({'error': f'2FA verification error: {str(e)}'}), 500


@accounts_bp.route('/<int:account_id>', methods=['PUT'])
@jwt_required
def update_account(account_id, current_user):
    """Update Telegram account settings"""
    account = TelegramAccount.query.get(account_id)
    
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    # Check ownership
    if current_user.web_role != 'admin' and account.owner_id != current_user.user_id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    if 'mode' in data:
        account.mode = data['mode']
    if 'daily_limit' in data:
        account.daily_limit = int(data['daily_limit'])
    if 'is_active' in data:
        account.is_active = bool(data['is_active'])
    
    try:
        db.session.commit()
        
        # Log update
        log_action(
            action='account_updated',
            user_id=current_user.user_id,
            details={
                'account_id': account_id,
                'updated_fields': list(data.keys()),
                'phone': account.phone
            }
        )
        
        return jsonify(account.to_dict())
    except Exception as e:
        db.session.rollback()
        log_error(e, 'account_update_failed', current_user.user_id, {'account_id': account_id})
        return jsonify({'error': str(e)}), 500


@accounts_bp.route('/<int:account_id>/chats', methods=['GET'])
@jwt_required
def get_account_chats(account_id, current_user):
    """Get list of chats from Telegram account"""
    account = TelegramAccount.query.get(account_id)
    
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    # Check ownership
    if current_user.web_role != 'admin' and account.owner_id != current_user.user_id:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        success, chats, error_msg = run_async(get_chats(account.phone))
        
        if not success:
            # Update account error
            account.last_error = error_msg
            db.session.commit()
            return jsonify({'error': error_msg}), 500
        
        # Cache chats to database
        if chats:
            cache_time = datetime.utcnow()
            for chat_data in chats:
                telegram_chat_id = str(chat_data.get('id', ''))
                if not telegram_chat_id:
                    continue
                
                # Find existing chat or create new
                existing_chat = Chat.query.filter_by(
                    telegram_chat_id=telegram_chat_id,
                    owner_type='user',
                    owner_account_id=account_id
                ).first()
                
                if existing_chat:
                    # Update existing chat
                    existing_chat.title = chat_data.get('title', existing_chat.title)
                    existing_chat.type = chat_data.get('type', existing_chat.type)
                    existing_chat.members_count = chat_data.get('members_count', 0)
                    existing_chat.cached_at = cache_time
                    existing_chat.is_active = True
                else:
                    # Create new cached chat
                    new_chat = Chat(
                        telegram_chat_id=telegram_chat_id,
                        title=chat_data.get('title', 'Unknown'),
                        type=chat_data.get('type', 'group'),
                        owner_type='user',
                        owner_account_id=account_id,
                        members_count=chat_data.get('members_count', 0),
                        cached_at=cache_time,
                        is_active=True
                    )
                    db.session.add(new_chat)
        
        # Update last_used
        account.last_used = datetime.utcnow()
        account.last_error = None
        db.session.commit()
        
        return jsonify({
            'success': True,
            'chats': chats or []
        })
    except Exception as e:
        logger.error(f"Error getting chats: {e}", exc_info=True)
        account.last_error = str(e)
        db.session.commit()
        log_error(e, 'account_get_chats_failed', current_user.user_id, {'account_id': account_id})
        return jsonify({'error': f'Error loading chats: {str(e)}'}), 500


@accounts_bp.route('/<int:account_id>/test-message', methods=['POST'])
@jwt_required
def send_test_message(account_id, current_user):
    """Send test message from Telegram account"""
    account = TelegramAccount.query.get(account_id)
    
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    # Check ownership
    if current_user.web_role != 'admin' and account.owner_id != current_user.user_id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    chat_id = data.get('chat_id', '').strip()
    message = data.get('message', 'Тестовое сообщение').strip()
    
    if not chat_id:
        return jsonify({'error': 'chat_id is required'}), 400
    
    try:
        success, error_msg, message_id = run_async(telethon_send_test_message(account.phone, chat_id, message))
        
        if not success:
            # Update account error
            account.last_error = error_msg
            account.last_used = datetime.utcnow()
            db.session.commit()
            return jsonify({'error': error_msg}), 500
        
        # Update last_used
        account.last_used = datetime.utcnow()
        account.last_error = None
        db.session.commit()
        
        log_action(
            action='account_test_message_sent',
            user_id=current_user.user_id,
            details={
                'account_id': account_id,
                'chat_id': chat_id,
                'message_id': message_id
            }
        )
        
        return jsonify({
            'success': True,
            'message_id': message_id,
            'message': 'Test message sent successfully'
        })
    except Exception as e:
        logger.error(f"Error sending test message: {e}", exc_info=True)
        account.last_error = str(e)
        account.last_used = datetime.utcnow()
        db.session.commit()
        log_error(e, 'account_test_message_failed', current_user.user_id, {'account_id': account_id})
        return jsonify({'error': f'Error sending message: {str(e)}'}), 500


@accounts_bp.route('/<int:account_id>/rate-limit-status', methods=['GET'])
@jwt_required
def get_rate_limit_status(account_id, current_user):
    """Get rate limit status for account"""
    from app.utils.rate_limiter import get_rate_limit_status as get_rate_status
    
    account = TelegramAccount.query.get(account_id)
    
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    # Check ownership
    if current_user.web_role != 'admin' and account.owner_id != current_user.user_id:
        return jsonify({'error': 'Access denied'}), 403
    
    status = get_rate_status(account.phone)
    return jsonify(status)


@accounts_bp.route('/<int:account_id>', methods=['DELETE'])
@jwt_required
def delete_account(account_id, current_user):
    """Delete Telegram account"""
    account = TelegramAccount.query.get(account_id)
    
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    # Check ownership
    if current_user.web_role != 'admin' and account.owner_id != current_user.user_id:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        account_info = {'account_id': account_id, 'phone': account.phone}
        
        # Delete session file if exists
        session_path = account.session_file
        if session_path and os.path.exists(session_path):
            try:
                os.remove(session_path)
            except Exception as e:
                logger.warning(f"Failed to delete session file {session_path}: {e}")
        
        db.session.delete(account)
        db.session.commit()
        
        # Log deletion
        log_action(
            action='account_deleted',
            user_id=current_user.user_id,
            details=account_info
        )
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        log_error(e, 'account_delete_failed', current_user.user_id, {'account_id': account_id})
        return jsonify({'error': str(e)}), 500

