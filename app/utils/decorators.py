"""
Decorators for authentication and authorization
"""
from functools import wraps
from flask import request, jsonify
from app.utils.jwt import verify_token, get_user_from_token
from app.models.user import User


def jwt_required(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Try to get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        # Try to get token from cookies
        if not token:
            token = request.cookies.get('jwt_token')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Add user to kwargs and request context
        user = User.query.get(payload.get('user_id'))
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        from flask import g
        g.current_user = user
        g.current_user_id = user.user_id
        kwargs['current_user'] = user
        return f(*args, **kwargs)
    
    return decorated


def role_required(*roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        @jwt_required
        def decorated(*args, **kwargs):
            user = kwargs.get('current_user')
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            if user.web_role not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator

