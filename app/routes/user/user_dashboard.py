"""
User dashboard routes
Логика: главная страница пользователя и статистика
"""
from flask import Blueprint, request, jsonify, render_template
from app.database import db
from app.models.object import Object
from app.models.publication_queue import PublicationQueue
from app.models.account_publication_queue import AccountPublicationQueue
from app.models.publication_history import PublicationHistory
from app.models.telegram_account import TelegramAccount
from app.models.quick_access import QuickAccess
from app.models.autopublish_config import AutopublishConfig
from app.models.chat_group import ChatGroup
from app.utils.decorators import jwt_required
from app.utils.logger import log_action, log_error
from sqlalchemy import func
from datetime import datetime
import logging

user_dashboard_bp = Blueprint('user_dashboard', __name__)
logger = logging.getLogger(__name__)

@user_dashboard_bp.route('/dashboard', methods=['GET'])
@jwt_required
def user_dashboard(current_user):
    """User dashboard page"""
    return render_template('user/dashboard.html', user=current_user)


@user_dashboard_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required
def user_stats(current_user):
    """Get user dashboard statistics"""
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
    
    # Total publications
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
    
    # Objects on autopublication (objects with enabled autopublish config)
    from app.models.autopublish_config import AutopublishConfig
    autopublish_objects = AutopublishConfig.query.filter_by(
        user_id=current_user.user_id,
        enabled=True
    ).count()
    
    return jsonify({
        'objects_count': objects_count,
        'objects_by_status': dict(objects_by_status),
        'today_publications': today_publications,
        'total_publications': total_publications,
        'accounts_count': accounts_count,
        'autopublish_objects_count': autopublish_objects
    })

