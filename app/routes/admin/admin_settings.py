"""
Admin settings routes
Логика: управление системными настройками (дубликаты, обход ограничения времени)
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.system_setting import SystemSetting
from app.utils.decorators import jwt_required, role_required
from app.utils.logger import log_action, log_error
import logging

admin_settings_bp = Blueprint('admin_settings', __name__)
logger = logging.getLogger(__name__)


@admin_settings_bp.route('/dashboard/settings', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_settings_data(current_user):
    """Get admin settings"""
    try:
        settings = {}
        
        # Получаем настройку дубликатов
        duplicates_setting = SystemSetting.query.filter_by(key='allow_duplicates').first()
        if duplicates_setting and isinstance(duplicates_setting.value_json, dict):
            settings['allow_duplicates'] = duplicates_setting.value_json.get('enabled', False)
        else:
            settings['allow_duplicates'] = False
        
        # Получаем настройку обхода ограничения времени для админа
        time_limit_setting = SystemSetting.query.filter_by(key='admin_bypass_time_limit').first()
        if time_limit_setting and isinstance(time_limit_setting.value_json, dict):
            settings['admin_bypass_time_limit'] = time_limit_setting.value_json.get('enabled', False)
        else:
            settings['admin_bypass_time_limit'] = False
        
        return jsonify({
            'success': True,
            'settings': settings
        })
    except Exception as e:
        logger.error(f"Error getting admin settings: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_settings_bp.route('/dashboard/settings/allow-duplicates', methods=['PUT'])
@jwt_required
@role_required('admin')
def admin_settings_allow_duplicates(current_user):
    """Update allow duplicates setting"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        
        setting = SystemSetting.query.filter_by(key='allow_duplicates').first()
        if not setting:
            setting = SystemSetting(
                key='allow_duplicates',
                value_json={'enabled': enabled},
                description='Разрешить дубликаты публикаций (24 часа)',
                updated_by=current_user.user_id
            )
            db.session.add(setting)
        else:
            setting.value_json = {'enabled': enabled}
            setting.updated_by = current_user.user_id
        
        db.session.commit()
        
        log_action(
            action='admin_settings_updated',
            user_id=current_user.user_id,
            details={'setting': 'allow_duplicates', 'enabled': enabled}
        )
        
        return jsonify({
            'success': True,
            'message': 'Setting updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating allow duplicates setting: {e}", exc_info=True)
        log_error(e, 'admin_settings_update_failed', current_user.user_id, {'setting': 'allow_duplicates'})
        return jsonify({'error': str(e)}), 500


@admin_settings_bp.route('/dashboard/settings/admin-bypass-time-limit', methods=['PUT'])
@jwt_required
@role_required('admin')
def admin_settings_bypass_time_limit(current_user):
    """Update admin bypass time limit setting"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        
        setting = SystemSetting.query.filter_by(key='admin_bypass_time_limit').first()
        if not setting:
            setting = SystemSetting(
                key='admin_bypass_time_limit',
                value_json={'enabled': enabled},
                description='Админ может публиковать в любое время (обход ограничения 8:00-22:00)',
                updated_by=current_user.user_id
            )
            db.session.add(setting)
        else:
            if not isinstance(setting.value_json, dict):
                setting.value_json = {}
            setting.value_json['enabled'] = enabled
            setting.updated_by = current_user.user_id
        
        db.session.commit()
        
        log_action(
            action='admin_settings_updated',
            user_id=current_user.user_id,
            details={'setting': 'admin_bypass_time_limit', 'enabled': enabled}
        )
        
        return jsonify({
            'success': True,
            'message': 'Setting updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating admin bypass time limit setting: {e}", exc_info=True)
        log_error(e, 'admin_settings_update_failed', current_user.user_id, {'setting': 'admin_bypass_time_limit'})
        return jsonify({'error': str(e)}), 500

