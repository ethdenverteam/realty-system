"""
Admin routes
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.user import User
from app.utils.decorators import jwt_required, role_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/users', methods=['GET'])
@jwt_required
@role_required('admin')
def list_users(current_user):
    """Get list of all users (admin only)"""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])


@admin_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@jwt_required
@role_required('admin')
def update_user_role(user_id, current_user):
    """Update user role (admin only)"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    if 'web_role' in data:
        user.web_role = data['web_role']
    if 'bot_role' in data:
        user.bot_role = data['bot_role']
    
    db.session.commit()
    
    return jsonify(user.to_dict())

