"""
Telegram accounts routes
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.telegram_account import TelegramAccount
from app.utils.decorators import jwt_required, role_required

accounts_bp = Blueprint('accounts', __name__)


@accounts_bp.route('/', methods=['GET'])
@jwt_required
def list_accounts(current_user):
    """Get list of user's Telegram accounts"""
    if current_user.web_role == 'admin':
        accounts = TelegramAccount.query.all()
    else:
        accounts = TelegramAccount.query.filter_by(owner_id=current_user.user_id).all()
    
    return jsonify([acc.to_dict() for acc in accounts])


@accounts_bp.route('/', methods=['POST'])
@jwt_required
def create_account(current_user):
    """Create new Telegram account (placeholder for Telethon integration)"""
    data = request.get_json()
    
    # TODO: Implement Telethon session creation
    # This is a placeholder
    return jsonify({'error': 'Not implemented yet'}), 501


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
    
    db.session.commit()
    
    return jsonify(account.to_dict())


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
    
    db.session.delete(account)
    db.session.commit()
    
    return jsonify({'success': True})

