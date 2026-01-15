"""
Database utilities for bot
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from urllib.parse import quote_plus
import os


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


# Database connection
DATABASE_URL = build_database_url()

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(bind=engine))


def get_db():
    """Get database session"""
    return SessionLocal()

