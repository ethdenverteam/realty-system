"""
Dashboard routes
"""
from flask import Blueprint, jsonify
from app.database import db
from app.models.object import Object
from app.models.user import User
from app.models.publication_queue import PublicationQueue
from app.utils.decorators import jwt_required
from datetime import datetime, timedelta
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required
def get_stats(current_user):
    """Get dashboard statistics"""
    # User's objects count
    objects_count = Object.query.filter_by(user_id=current_user.user_id).count()
    
    # Objects by status
    objects_by_status = db.session.query(
        Object.status,
        func.count(Object.object_id)
    ).filter_by(user_id=current_user.user_id).group_by(Object.status).all()
    
    # Today's publications
    today = datetime.utcnow().date()
    today_publications = PublicationQueue.query.filter(
        PublicationQueue.user_id == current_user.user_id,
        func.date(PublicationQueue.created_at) == today
    ).count()
    
    return jsonify({
        'objects_count': objects_count,
        'objects_by_status': dict(objects_by_status),
        'today_publications': today_publications
    })

