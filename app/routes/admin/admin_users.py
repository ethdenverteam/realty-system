"""
Admin users management routes
Логика: управление пользователями, изменение ролей, добавление админов
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.user import User
from app.utils.decorators import jwt_required, role_required
from app.utils.logger import log_action, log_error
import logging

admin_users_bp = Blueprint('admin_users', __name__)
logger = logging.getLogger(__name__)


@admin_users_bp.route('/dashboard/users', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_users(current_user):
    """Get list of all users"""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])


@admin_users_bp.route('/dashboard/users/<int:user_id>/role', methods=['PUT'])
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


@admin_users_bp.route('/dashboard/users/add-admin-by-telegram-id', methods=['POST'])
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

