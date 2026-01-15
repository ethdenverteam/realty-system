"""
Authentication routes
"""
from flask import Blueprint, request, jsonify, make_response, render_template
from app.database import db
from app.models.user import User
from app.models.bot_web_code import BotWebCode
from app.utils.jwt import generate_token
from datetime import datetime, timedelta
import random
import string

auth_bp = Blueprint('auth', __name__)


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
    
    # Mark code as used
    bot_code.is_used = True
    db.session.commit()
    
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
    response = make_response(jsonify({'success': True}))
    response.set_cookie('jwt_token', '', expires=0)
    return response


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
    return render_template('login.html')

