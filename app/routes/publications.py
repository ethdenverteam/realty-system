"""
Publications routes
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.publication_queue import PublicationQueue
from app.models.object import Object
from app.utils.decorators import jwt_required

publications_bp = Blueprint('publications', __name__)


@publications_bp.route('/queue', methods=['POST'])
@jwt_required
def create_publication(current_user):
    """Create publication task"""
    data = request.get_json()
    
    object_id = data.get('object_id')
    chat_ids = data.get('chat_ids', [])
    account_id = data.get('account_id')
    mode = data.get('mode', 'immediate')
    
    if not object_id:
        return jsonify({'error': 'object_id is required'}), 400
    
    obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
    if not obj:
        return jsonify({'error': 'Object not found'}), 404
    
    # Create queue entries
    queue_ids = []
    for chat_id in chat_ids:
        queue = PublicationQueue(
            object_id=object_id,
            chat_id=chat_id,
            account_id=account_id,
            user_id=current_user.user_id,
            type='user' if account_id else 'bot',
            mode=mode,
            status='pending'
        )
        db.session.add(queue)
        queue_ids.append(queue.queue_id)
    
    db.session.commit()
    
    # TODO: Add to Celery queue
    
    return jsonify({
        'success': True,
        'queue_ids': queue_ids
    }), 201

