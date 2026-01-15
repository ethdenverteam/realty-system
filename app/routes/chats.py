"""
Chats routes
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.chat import Chat
from app.utils.decorators import jwt_required

chats_bp = Blueprint('chats', __name__)


@chats_bp.route('/', methods=['GET'])
@jwt_required
def list_chats(current_user):
    """Get list of chats"""
    chats = Chat.query.filter_by(is_active=True).all()
    return jsonify([chat.to_dict() for chat in chats])


@chats_bp.route('/<int:chat_id>', methods=['PUT'])
@jwt_required
def update_chat(chat_id, current_user):
    """Update chat settings"""
    chat = Chat.query.get(chat_id)
    
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404
    
    data = request.get_json()
    
    if 'category' in data:
        chat.category = data['category']
    if 'is_active' in data:
        chat.is_active = bool(data['is_active'])
    
    db.session.commit()
    
    return jsonify(chat.to_dict())

