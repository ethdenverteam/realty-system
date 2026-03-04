"""
Admin logs routes
Логика: просмотр логов действий пользователей
"""
from flask import Blueprint, request, jsonify, render_template
from app.models.action_log import ActionLog
from app.utils.decorators import jwt_required, role_required
from sqlalchemy import desc
import logging

admin_logs_bp = Blueprint('admin_logs', __name__)
logger = logging.getLogger(__name__)


@admin_logs_bp.route('/dashboard/logs', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_logs_page(current_user):
    """Logs viewer page"""
    return render_template('admin/logs.html', user=current_user)


@admin_logs_bp.route('/dashboard/logs/data', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_logs_data(current_user):
    """Get logs data"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    action = request.args.get('action')
    user_id = request.args.get('user_id', type=int)
    
    query = ActionLog.query
    
    if action:
        query = query.filter(ActionLog.action == action)
    if user_id:
        query = query.filter(ActionLog.user_id == user_id)
    
    query = query.order_by(desc(ActionLog.created_at))
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

