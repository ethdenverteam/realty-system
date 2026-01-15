"""
Database configuration and initialization
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

db = SQLAlchemy()


def init_db():
    """Initialize database tables"""
    from app.models import (
        User, Object, TelegramAccount, Chat, PublicationQueue,
        PublicationHistory, ActionLog, Statistics, BotWebCode, SystemSetting
    )
    db.create_all()

