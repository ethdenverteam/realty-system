"""
Objects routes package
Логика: объединение всех objects blueprint'ов в один для регистрации в app
"""
from flask import Blueprint

# Импортируем все blueprint'ы
from app.routes.objects_handlers.objects_pages import objects_pages_bp
from app.routes.objects_handlers.objects_crud import objects_crud_bp

# Создаем главный blueprint для объединения всех objects routes
objects_bp = Blueprint('objects', __name__)

# Регистрируем все под-blueprint'ы
objects_bp.register_blueprint(objects_pages_bp)
objects_bp.register_blueprint(objects_crud_bp)

