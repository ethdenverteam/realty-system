"""
Application configuration
"""
import os
from datetime import timezone

# Глобальная переменная часового пояса системы
# Можно менять в будущем, сейчас установлена МСК (GMT+3)
SYSTEM_TIMEZONE = 'Europe/Moscow'  # МСК (GMT+3)
SYSTEM_TIMEZONE_NAME = 'МСК'

# Время работы автопубликации (по МСК)
AUTOPUBLISH_START_HOUR = 8  # Начало работы: 8:00 МСК
AUTOPUBLISH_END_HOUR = 22   # Конец работы: 22:00 МСК

class Config:
    """Application configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:password@localhost/realty_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_DELTA = 86400  # 24 hours
