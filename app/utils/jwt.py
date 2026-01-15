"""
JWT utilities for authentication
"""
import jwt
from datetime import datetime, timedelta
from flask import current_app
from app.models.user import User


def generate_token(user: User) -> str:
    """Generate JWT token for user"""
    payload = {
        'user_id': user.user_id,
        'telegram_id': user.telegram_id,
        'web_role': user.web_role,
        'exp': datetime.utcnow() + timedelta(seconds=current_app.config['JWT_EXPIRATION_DELTA']),
        'iat': datetime.utcnow(),
    }
    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm=current_app.config['JWT_ALGORITHM']
    )
    return token


def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=[current_app.config['JWT_ALGORITHM']]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_from_token(token: str) -> User:
    """Get user from JWT token"""
    payload = verify_token(token)
    if not payload:
        return None
    
    user_id = payload.get('user_id')
    if not user_id:
        return None
    
    return User.query.get(user_id)

