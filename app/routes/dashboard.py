"""
Dashboard routes
"""
from flask import Blueprint, jsonify, render_template, redirect
from app.database import db
from app.models.object import Object
from app.models.user import User
from app.models.publication_queue import PublicationQueue
from app.utils.decorators import jwt_required, role_required
from datetime import datetime, timedelta
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/', methods=['GET'])
@jwt_required
def dashboard_page(current_user):
    """Show dashboard page (redirects to admin or user dashboard)"""
    if current_user.web_role == 'admin':
        return redirect('/system/admin/dashboard')
    return redirect('/system/user/dashboard')


@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required
def get_stats(current_user):
    """Get dashboard statistics"""
    from app.models.telegram_account import TelegramAccount
    from app.models.publication_history import PublicationHistory
    
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
    
    # Total publications (filter through objects)
    total_publications = db.session.query(PublicationHistory).join(
        Object, PublicationHistory.object_id == Object.object_id
    ).filter(
        Object.user_id == current_user.user_id
    ).count()
    
    # Accounts count
    accounts_count = TelegramAccount.query.filter_by(
        owner_id=current_user.user_id,
        is_active=True
    ).count()
    
    return jsonify({
        'objects_count': objects_count,
        'objects_by_status': dict(objects_by_status),
        'today_publications': today_publications,
        'total_publications': total_publications,
        'accounts_count': accounts_count
    })

