"""
Database utilities for bot - унифицировано с app.database
Использует единую БД через app.database
"""
from app.database import db


def get_db():
    """
    Get database session - использует единую БД через app.database
    Для обратной совместимости с существующим кодом
    """
    # Возвращаем db.session для использования в боте
    # В Flask контексте это работает автоматически
    # Вне Flask контекста нужно использовать db.session напрямую
    return db.session

