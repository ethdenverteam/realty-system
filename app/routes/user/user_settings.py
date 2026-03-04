"""
User settings routes
Логика: настройки пользователя, очистка автопубликации, проверка очередей
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

user_settings_bp = Blueprint('user_settings', __name__)
logger = logging.getLogger(__name__)

@user_settings_bp.route('/dashboard/settings', methods=['GET'])
@jwt_required
def user_settings_page(current_user):
    """User settings page"""
    return render_template('user/settings.html', user=current_user)


@user_settings_bp.route('/dashboard/districts', methods=['GET'])
@jwt_required
def get_user_districts(current_user):
    """Get all districts for user forms"""
    from app.models.system_setting import SystemSetting
    
    districts_setting = SystemSetting.query.filter_by(key='districts_config').first()
    districts_config = districts_setting.value_json if districts_setting else {}
    
    # Convert dict to list of district names
    districts_list = list(districts_config.keys()) if isinstance(districts_config, dict) else []
    
    return jsonify({
        'districts': districts_list
    })


@user_settings_bp.route('/dashboard/settings/data', methods=['GET'])
@jwt_required
def get_user_settings(current_user):
    """Get user settings"""
    settings = current_user.settings_json or {}
    return jsonify({
        'phone': current_user.phone or '',
        'contact_name': settings.get('contact_name', ''),
        'default_show_username': settings.get('default_show_username', False)
    })


@user_settings_bp.route('/dashboard/settings/data', methods=['PUT'])
@jwt_required
def update_user_settings(current_user):
    """Update user settings"""
    data = request.get_json()
    
    # Validate phone number format if provided
    if 'phone' in data and data['phone']:
        phone = data['phone'].strip()
        import re
        phone_pattern = re.compile(r'^8\d{10}$')
        if not phone_pattern.match(phone):
            return jsonify({
                'error': 'Некорректный номер телефона',
                'details': 'Номер должен быть в формате 89693386969 (11 цифр, начинается с 8)'
            }), 400
        current_user.phone = phone
    elif 'phone' in data:
        current_user.phone = None
    
    if not current_user.settings_json:
        current_user.settings_json = {}
    
    # Создаем новый словарь для отслеживания изменений SQLAlchemy
    settings = dict(current_user.settings_json) if current_user.settings_json else {}
    
    if 'contact_name' in data:
        settings['contact_name'] = data['contact_name'] or ''
    
    if 'default_show_username' in data:
        settings['default_show_username'] = bool(data['default_show_username'])
    
    current_user.settings_json = settings
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(current_user, 'settings_json')
    
    try:
        db.session.commit()
        
        log_action(
            action='user_settings_updated',
            user_id=current_user.user_id,
            details={
                'updated_fields': list(data.keys())
            }
        )
        
        # Перезагружаем пользователя для получения актуальных данных
        db.session.refresh(current_user)
        settings = current_user.settings_json or {}
        
        return jsonify({
            'phone': current_user.phone or '',
            'contact_name': settings.get('contact_name', ''),
            'default_show_username': settings.get('default_show_username', False)
        })
    except Exception as e:
        db.session.rollback()
        log_error(e, 'user_settings_update_failed', current_user.user_id, {})
        return jsonify({'error': str(e)}), 500


@user_settings_bp.route('/dashboard/settings/clear-autopublish', methods=['POST'])
@jwt_required
def clear_autopublish_and_queues(current_user):
    """Clear all autopublish configs and queues for user"""
    try:
        # Удаляем все конфигурации автопубликации пользователя
        autopublish_configs = AutopublishConfig.query.filter_by(user_id=current_user.user_id).all()
        configs_count = len(autopublish_configs)
        for config in autopublish_configs:
            db.session.delete(config)
        
        # Получаем ID всех очередей публикаций с автопубликацией для пользователя
        # Используем no_autoflush, чтобы избежать преждевременного flush
        with db.session.no_autoflush:
            publication_queues = PublicationQueue.query.filter_by(
                user_id=current_user.user_id,
                mode='autopublish'
            ).all()
            queues_count = len(publication_queues)
            queue_ids = [q.queue_id for q in publication_queues]
        
        # Сначала обнуляем ссылки в PublicationHistory, чтобы избежать нарушения внешнего ключа
        if queue_ids:
            PublicationHistory.query.filter(
                PublicationHistory.queue_id.in_(queue_ids)
            ).update({PublicationHistory.queue_id: None}, synchronize_session=False)
            db.session.commit()  # Фиксируем обнуление ссылок
        
        # Теперь удаляем очереди
        if queue_ids:
            PublicationQueue.query.filter(
                PublicationQueue.queue_id.in_(queue_ids)
            ).delete(synchronize_session=False)
        
        # Получаем ID всех очередей публикаций для аккаунтов пользователя
        with db.session.no_autoflush:
            account_queues = AccountPublicationQueue.query.filter_by(user_id=current_user.user_id).all()
            account_queues_count = len(account_queues)
            account_queue_ids = [q.queue_id for q in account_queues]
        
        # Проверяем, есть ли модель AppPublicationHistory, которая может ссылаться на AccountPublicationQueue
        # Если есть, обнуляем ссылки
        try:
            from app.models.app_publication_history import AppPublicationHistory
            if account_queue_ids:
                # Проверяем, есть ли поле queue_id в AppPublicationHistory
                if hasattr(AppPublicationHistory, 'queue_id'):
                    AppPublicationHistory.query.filter(
                        AppPublicationHistory.queue_id.in_(account_queue_ids)
                    ).update({AppPublicationHistory.queue_id: None}, synchronize_session=False)
                    db.session.commit()  # Фиксируем обнуление ссылок
        except ImportError:
            # Модель не существует или не импортируется - пропускаем
            pass
        
        # Удаляем очереди для аккаунтов
        if account_queue_ids:
            AccountPublicationQueue.query.filter(
                AccountPublicationQueue.queue_id.in_(account_queue_ids)
            ).delete(synchronize_session=False)
        
        db.session.commit()
        
        log_action(
            action='autopublish_cleared',
            user_id=current_user.user_id,
            details={
                'configs_deleted': configs_count,
                'publication_queues_deleted': queues_count,
                'account_queues_deleted': account_queues_count
            }
        )
        
        return jsonify({
            'success': True,
            'message': 'Автопубликация и очереди успешно очищены',
            'deleted': {
                'configs': configs_count,
                'publication_queues': queues_count,
                'account_queues': account_queues_count
            }
        })
    except Exception as e:
        db.session.rollback()
        log_error(e, 'clear_autopublish_failed', current_user.user_id, {})
        return jsonify({'error': str(e)}), 500


@user_settings_bp.route('/dashboard/settings/check-account-queues', methods=['GET'])
@jwt_required
def check_account_autopublish_queues(current_user):
    """Проверить очереди автопубликации для аккаунтов пользователя"""
    try:
        from app.models.account_publication_queue import AccountPublicationQueue
        from app.models.autopublish_config import AutopublishConfig
        
        # Получаем все очереди пользователя
        queues = AccountPublicationQueue.query.filter_by(
            user_id=current_user.user_id
        ).order_by(AccountPublicationQueue.created_at.desc()).limit(100).all()
        
        # Группируем по статусам
        queues_by_status = {}
        for queue in queues:
            status = queue.status
            if status not in queues_by_status:
                queues_by_status[status] = []
            queues_by_status[status].append({
                'queue_id': queue.queue_id,
                'object_id': queue.object_id,
                'chat_id': queue.chat_id,
                'account_id': queue.account_id,
                'status': queue.status,
                'scheduled_time': queue.scheduled_time.isoformat() if queue.scheduled_time else None,
                'created_at': queue.created_at.isoformat() if queue.created_at else None,
                'attempts': queue.attempts,
                'error_message': queue.error_message
            })
        
        # Проверяем конфигурации автопубликации
        configs = AutopublishConfig.query.filter_by(user_id=current_user.user_id).all()
        configs_info = []
        for cfg in configs:
            accounts_enabled = False
            if cfg.accounts_config_json and isinstance(cfg.accounts_config_json, dict):
                accounts = cfg.accounts_config_json.get('accounts', [])
                accounts_enabled = len(accounts) > 0
            
            configs_info.append({
                'object_id': cfg.object_id,
                'enabled': cfg.enabled,
                'bot_enabled': cfg.bot_enabled,
                'accounts_enabled': accounts_enabled,
                'accounts_count': len(cfg.accounts_config_json.get('accounts', [])) if cfg.accounts_config_json else 0
            })
        
        return jsonify({
            'success': True,
            'queues': {
                'total': len(queues),
                'by_status': queues_by_status
            },
            'configs': configs_info,
            'summary': {
                'pending': len([q for q in queues if q.status == 'pending']),
                'processing': len([q for q in queues if q.status == 'processing']),
                'completed': len([q for q in queues if q.status == 'completed']),
                'failed': len([q for q in queues if q.status == 'failed']),
                'flood_wait': len([q for q in queues if q.status == 'flood_wait'])
            }
        }), 200
    except Exception as e:
        log_error(e, 'check_account_queues_failed', current_user.user_id, {})
