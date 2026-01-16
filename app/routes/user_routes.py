"""
User routes - реорганизованные пользовательские роуты
"""
from flask import Blueprint, request, jsonify, render_template
from app.database import db
from app.models.object import Object
from app.models.publication_queue import PublicationQueue
from app.models.publication_history import PublicationHistory
from app.models.telegram_account import TelegramAccount
from app.utils.decorators import jwt_required
from app.utils.logger import log_action, log_error
from sqlalchemy import func
from datetime import datetime
import logging

user_routes_bp = Blueprint('user_routes', __name__)
logger = logging.getLogger(__name__)


@user_routes_bp.route('/dashboard', methods=['GET'])
@jwt_required
def user_dashboard(current_user):
    """User dashboard page"""
    return render_template('user/dashboard.html', user=current_user)


@user_routes_bp.route('/dashboard/stats', methods=['GET'])
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
    
    return jsonify({
        'objects_count': objects_count,
        'objects_by_status': dict(objects_by_status),
        'today_publications': today_publications,
        'total_publications': total_publications,
        'accounts_count': accounts_count
    })


@user_routes_bp.route('/dashboard/objects', methods=['GET'])
@jwt_required
def user_objects_page(current_user):
    """Objects list page"""
    return render_template('user/objects.html', user=current_user)


@user_routes_bp.route('/dashboard/objects/list', methods=['GET'])
@jwt_required
def user_objects_list(current_user):
    """Get list of user's objects"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    rooms_type = request.args.get('rooms_type')
    search = request.args.get('search')
    sort_by = request.args.get('sort_by', 'creation_date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Build query
    query = Object.query.filter_by(user_id=current_user.user_id)
    
    # Apply filters
    if status:
        query = query.filter(Object.status == status)
    if rooms_type:
        query = query.filter(Object.rooms_type == rooms_type)
    if search:
        from sqlalchemy import or_
        search_filter = or_(
            Object.object_id.ilike(f'%{search}%'),
            Object.address.ilike(f'%{search}%'),
            Object.comment.ilike(f'%{search}%')
        )
        query = query.filter(search_filter)
    
    # Apply sorting
    if sort_by == 'price':
        order_by = Object.price.desc() if sort_order == 'desc' else Object.price.asc()
    elif sort_by == 'publication_date':
        order_by = Object.publication_date.desc() if sort_order == 'desc' else Object.publication_date.asc()
    else:  # creation_date
        order_by = Object.creation_date.desc() if sort_order == 'desc' else Object.creation_date.asc()
    
    query = query.order_by(order_by)
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'objects': [obj.to_dict() for obj in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })


@user_routes_bp.route('/dashboard/objects/create', methods=['GET'])
@jwt_required
def user_create_object_page(current_user):
    """Create object page"""
    return render_template('user/create_object.html', user=current_user)

