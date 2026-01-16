"""
Authentication routes
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
    """Login with 6-digit code from bot"""
    data = request.get_json()
    code = data.get('code', '').strip()
    
    if not code or len(code) != 6:
        return jsonify({'error': 'Invalid code format'}), 400
    
    # Find code in database
    bot_code = BotWebCode.query.filter_by(code=code).first()
    
    if not bot_code:
        return jsonify({'error': 'Invalid code'}), 404
    
    if bot_code.is_used:
        return jsonify({'error': 'Code already used'}), 400
    
    if datetime.utcnow() > bot_code.expires_at:
        return jsonify({'error': 'Code expired'}), 400
    
    # Get user
    user = User.query.get(bot_code.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Auto-assign admin role if user is ADMIN_ID
    from app.config import Config
    if user.telegram_id == Config.ADMIN_ID and user.web_role != 'admin':
        user.web_role = 'admin'
        logger.info(f"Auto-assigned admin role to user {user.user_id} (telegram_id: {user.telegram_id})")
    
    # Mark code as used
    bot_code.is_used = True
    db.session.commit()
    
    # Log successful login
    log_action(
        action='user_login',
        user_id=user.user_id,
        details={
            'method': 'bot_code',
            'username': user.username,
            'telegram_id': user.telegram_id
        },
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string if request.user_agent else None
    )
    
    # Generate JWT token
    token = generate_token(user)
    
    # Create response with token in cookie
    response = make_response(jsonify({
        'success': True,
        'user': user.to_dict(),
        'token': token
    }))
    
    response.set_cookie(
        'jwt_token',
        token,
        max_age=7 * 24 * 60 * 60,  # 7 days
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite='Lax'
    )
    
    return response


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

