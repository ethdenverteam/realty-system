"""
Publications routes
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.publication_queue import PublicationQueue
from app.models.object import Object
from app.models.publication_history import PublicationHistory
from app.utils.decorators import jwt_required
from app.utils.logger import log_action, log_error
from datetime import datetime, timedelta
import logging

publications_bp = Blueprint('publications', __name__)
logger = logging.getLogger(__name__)


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
    
    # Check if object was published to any of the chats within last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_publications = PublicationHistory.query.filter(
        PublicationHistory.object_id == object_id,
        PublicationHistory.chat_id.in_(chat_ids),
        PublicationHistory.published_at >= yesterday,
        PublicationHistory.deleted == False
    ).all()
    
    if recent_publications:
        blocked_chats = [p.chat_id for p in recent_publications]
        return jsonify({
            'error': 'Object was already published to some chats within 24 hours',
            'blocked_chat_ids': blocked_chats
        }), 400
    
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
    
    try:
        db.session.commit()
        
        # Log publication creation
        log_action(
            action='publication_queued',
            user_id=current_user.user_id,
            details={
                'object_id': object_id,
                'chat_count': len(chat_ids),
                'account_id': account_id,
                'mode': mode,
                'queue_ids': queue_ids
            }
        )
        
        # TODO: Add to Celery queue
        
        return jsonify({
            'success': True,
            'queue_ids': queue_ids
        }), 201
    except Exception as e:
        db.session.rollback()
        log_error(e, 'publication_queue_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({'error': str(e)}), 500

