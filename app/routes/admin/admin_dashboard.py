"""
Admin dashboard routes
Логика: отображение главной страницы админки и статистики
"""
from flask import Blueprint, jsonify, render_template
from app.database import db
from app.models.user import User
from app.models.object import Object
from app.models.telegram_account import TelegramAccount
from app.models.publication_queue import PublicationQueue
from app.utils.decorators import jwt_required, role_required
from sqlalchemy import func
from datetime import datetime
import logging

admin_dashboard_bp = Blueprint('admin_dashboard', __name__)
logger = logging.getLogger(__name__)


@admin_dashboard_bp.route('/dashboard', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_dashboard(current_user):
    """Admin dashboard page"""
    return render_template('admin/dashboard.html', user=current_user)


@admin_dashboard_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_stats(current_user):
    """Get admin statistics"""
    # Total users
    users_count = User.query.count()
    
    # Total objects
    objects_count = Object.query.count()
    
    # Publications today
    today = datetime.utcnow().date()
    publications_today = PublicationQueue.query.filter(
        func.date(PublicationQueue.created_at) == today
    ).count()
    
    # Active accounts
    accounts_count = TelegramAccount.query.filter_by(is_active=True).count()
    
    return jsonify({
        'users_count': users_count,
        'objects_count': objects_count,
        'publications_today': publications_today,
        'accounts_count': accounts_count
    })

