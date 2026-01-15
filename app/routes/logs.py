"""
Logs routes - просмотр логов действий
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.action_log import ActionLog
from app.utils.decorators import jwt_required, role_required
from datetime import datetime, timedelta
from sqlalchemy import desc, or_

logs_bp = Blueprint('logs', __name__)


@logs_bp.route('/', methods=['GET'])
@jwt_required
@role_required('admin')
def list_logs(current_user):
    """Get list of action logs (admin only)"""
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    action = request.args.get('action')
    user_id = request.args.get('user_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    search = request.args.get('search')
    
    # Build query
    query = ActionLog.query
    
    # Apply filters
    if action:
        query = query.filter(ActionLog.action == action)
    
    if user_id:
        query = query.filter(ActionLog.user_id == user_id)
    
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(ActionLog.created_at >= date_from_dt)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(ActionLog.created_at <= date_to_dt)
        except ValueError:
            pass
    
    if search:
        search_filter = or_(
            ActionLog.action.ilike(f'%{search}%'),
            ActionLog.ip_address.ilike(f'%{search}%'),
            ActionLog.user_agent.ilike(f'%{search}%')
        )
        query = query.filter(search_filter)
    
    # Order by date (newest first)
    query = query.order_by(desc(ActionLog.created_at))
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'logs': [log.to_dict() for log in pagination.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    })


@logs_bp.route('/actions', methods=['GET'])
@jwt_required
@role_required('admin')
def list_actions(current_user):
    """Get list of unique actions (admin only)"""
    actions = db.session.query(ActionLog.action).distinct().all()
    return jsonify({
        'actions': [action[0] for action in actions]
    })


@logs_bp.route('/stats', methods=['GET'])
@jwt_required
@role_required('admin')
def get_log_stats(current_user):
    """Get log statistics (admin only)"""
    from sqlalchemy import func
    
    # Total logs
    total_logs = ActionLog.query.count()
    
    # Logs by action (top 10)
    top_actions = db.session.query(
        ActionLog.action,
        func.count(ActionLog.log_id).label('count')
    ).group_by(ActionLog.action).order_by(desc('count')).limit(10).all()
    
    # Logs by day (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    logs_by_day = db.session.query(
        func.date(ActionLog.created_at).label('date'),
        func.count(ActionLog.log_id).label('count')
    ).filter(
        ActionLog.created_at >= seven_days_ago
    ).group_by(func.date(ActionLog.created_at)).order_by('date').all()
    
    # Error count (last 24 hours)
    last_24h = datetime.utcnow() - timedelta(hours=24)
    error_count = ActionLog.query.filter(
        ActionLog.action.like('error_%'),
        ActionLog.created_at >= last_24h
    ).count()
    
    return jsonify({
        'total_logs': total_logs,
        'top_actions': [{'action': a[0], 'count': a[1]} for a in top_actions],
        'logs_by_day': [{'date': str(d[0]), 'count': d[1]} for d in logs_by_day],
        'errors_last_24h': error_count
    })

