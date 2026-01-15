"""
Database utilities for bot
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os

# Database connection
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://realty_user:realty_password@localhost:5432/realty_db'
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(bind=engine))


def get_db():
    """Get database session"""
    return SessionLocal()

