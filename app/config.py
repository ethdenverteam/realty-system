"""
Application configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://realty_user:realty_password@localhost:5432/realty_db'
    )
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

