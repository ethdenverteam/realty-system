"""
Application configuration
"""
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()


def build_database_url():
    """Build DATABASE_URL from components, properly escaping special characters"""
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url
    
    # Build from components if DATABASE_URL not set
    db_user = os.getenv('POSTGRES_USER', 'realty_user')
    db_password = os.getenv('POSTGRES_PASSWORD', 'realty_password')
    db_host = os.getenv('POSTGRES_HOST', 'postgres')
    db_port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'realty_db')
    
    # Properly escape password and username
    safe_user = quote_plus(db_user)
    safe_password = quote_plus(db_password)
    
    return f'postgresql://{safe_user}:{safe_password}@{db_host}:{db_port}/{db_name}'


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = build_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('FLASK_ENV') == 'development'
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_DELTA = 7 * 24 * 60 * 60  # 7 days in seconds
    
    # Redis Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
    CHANNEL_ID = int(os.getenv('CHANNEL_ID', '0'))
    
    # File Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
    
    # Session files
    SESSIONS_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sessions')
    
    # Logging
    LOG_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')

