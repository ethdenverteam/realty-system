"""
API роуты для аутентификации пользователей
Цель: вход по коду из бота, выход, получение информации о текущем пользователе
Логика: все попытки входа логируются для безопасности
"""
from flask import Blueprint, request, jsonify, make_response, render_template, g
from app.database import db
from app.models.user import User
from app.models.bot_web_code import BotWebCode
from app.utils.jwt import generate_token
from app.utils.logger import log_action, log_error
from datetime import datetime, timedelta
import random
import string
import logging

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Вход пользователя по 6-значному коду из бота
    Логика: проверка формата кода, поиск в БД, проверка срока действия, генерация JWT токена
    Все попытки входа (успешные и неуспешные) логируются для безопасности
    """
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        ip_address = request.remote_addr
        user_agent = request.user_agent.string if request.user_agent else None
        
        logger.info(f"Login attempt with code from IP {ip_address}")
        
        # Проверка формата кода
        if not code or len(code) != 6:
            logger.warning(f"Invalid code format from IP {ip_address}: length={len(code) if code else 0}")
            log_action(
                action='user_login_failed',
                user_id=None,
                details={'reason': 'invalid_format', 'code_length': len(code) if code else 0},
                ip_address=ip_address,
                user_agent=user_agent
            )
            return jsonify({'error': 'Invalid code format'}), 400
        
        # Поиск кода в БД
        bot_code = BotWebCode.query.filter_by(code=code).first()
        
        if not bot_code:
            logger.warning(f"Invalid code from IP {ip_address}")
            log_action(
                action='user_login_failed',
                user_id=None,
                details={'reason': 'invalid_code'},
                ip_address=ip_address,
                user_agent=user_agent
            )
            return jsonify({'error': 'Invalid code'}), 404
        
        # Проверка использования кода
        if bot_code.is_used:
            logger.warning(f"Already used code from IP {ip_address}, user_id={bot_code.user_id}")
            log_action(
                action='user_login_failed',
                user_id=bot_code.user_id,
                details={'reason': 'code_already_used'},
                ip_address=ip_address,
                user_agent=user_agent
            )
            return jsonify({'error': 'Code already used'}), 400
        
        # Проверка срока действия кода
        if datetime.utcnow() > bot_code.expires_at:
            logger.warning(f"Expired code from IP {ip_address}, user_id={bot_code.user_id}")
            log_action(
                action='user_login_failed',
                user_id=bot_code.user_id,
                details={'reason': 'code_expired'},
                ip_address=ip_address,
                user_agent=user_agent
            )
            return jsonify({'error': 'Code expired'}), 400
        
        # Получаем пользователя
        user = User.query.get(bot_code.user_id)
        if not user:
            logger.error(f"User not found for code, user_id={bot_code.user_id}")
            log_action(
                action='user_login_failed',
                user_id=bot_code.user_id,
                details={'reason': 'user_not_found'},
                ip_address=ip_address,
                user_agent=user_agent
            )
            return jsonify({'error': 'User not found'}), 404
        
        # Автоматическое назначение роли админа для ADMIN_ID
        from app.config import Config
        if user.telegram_id == Config.ADMIN_ID and user.web_role != 'admin':
            user.web_role = 'admin'
            logger.info(f"Auto-assigned admin role to user {user.user_id} (telegram_id: {user.telegram_id})")
        
        # Помечаем код как использованный
        bot_code.is_used = True
        db.session.commit()
        
        # Логируем успешный вход
        logger.info(f"User {user.user_id} logged in successfully from IP {ip_address}")
        log_action(
            action='user_login',
            user_id=user.user_id,
            details={
                'method': 'bot_code',
                'username': user.username,
                'telegram_id': user.telegram_id,
                'web_role': user.web_role
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Генерируем JWT токен
        token = generate_token(user)
        
        # Создаём ответ с токеном в cookie
        response = make_response(jsonify({
            'success': True,
            'user': user.to_dict(),
            'token': token
        }))
        
        response.set_cookie(
            'jwt_token',
            token,
            max_age=7 * 24 * 60 * 60,  # 7 дней
            httponly=True,
            secure=False,  # В продакшене с HTTPS установить True
            samesite='Lax'
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in login: {e}", exc_info=True)
        log_error(
            error=e,
            action='user_login',
            details={'ip_address': request.remote_addr}
        )
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout user"""
    from app.utils.decorators import jwt_required
    
    @jwt_required
    def _logout(current_user):
        # Log logout
        log_action(
            action='user_logout',
            user_id=current_user.user_id,
            details={'username': current_user.username}
        )
        
        response = make_response(jsonify({'success': True}))
        response.set_cookie('jwt_token', '', expires=0)
        return response
    
    return _logout()


@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user info"""
    from app.utils.decorators import jwt_required
    
    @jwt_required
    def _get_user(current_user):
        return jsonify({'user': current_user.to_dict()})
    
    return _get_user()


@auth_bp.route('/bot-info', methods=['GET'])
def get_bot_info():
    """Get bot information (username)"""
    try:
        from bot.config import BOT_TOKEN
        import requests
        
        if not BOT_TOKEN:
            return jsonify({'username': None}), 200
        
        # Get bot info from Telegram API
        bot_info_url = f'https://api.telegram.org/bot{BOT_TOKEN}/getMe'
        try:
            response = requests.get(bot_info_url, timeout=5)
            data = response.json()
            if data.get('ok') and data.get('result'):
                username = data['result'].get('username')
                return jsonify({'username': username})
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
        
        return jsonify({'username': None}), 200
    except Exception as e:
        logger.error(f"Error in get_bot_info: {e}")
        return jsonify({'username': None}), 200


@auth_bp.route('/login', methods=['GET'])
def login_page():
    """Login page"""
    # Check if already logged in
    from flask import request
    token = request.cookies.get('jwt_token')
    if token:
        # Try to verify token and redirect
        try:
            from app.utils.jwt import verify_token
            user_data = verify_token(token)
            if user_data:
                from app.models.user import User
                user = User.query.get(user_data.get('user_id'))
                if user:
                    if user.web_role == 'admin':
                        from flask import redirect
                        return redirect('/system/admin/dashboard')
                    else:
                        from flask import redirect
                        return redirect('/system/user/dashboard')
        except:
            pass
    return render_template('login.html')

