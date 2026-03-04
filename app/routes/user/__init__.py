"""
User routes package
Логика: объединение всех user blueprint'ов в один для регистрации в app
"""
from flask import Blueprint

# Импортируем все blueprint'ы
from app.routes.user.user_dashboard import user_dashboard_bp
from app.routes.user.user_autopublish import user_autopublish_bp
from app.routes.user.user_objects import user_objects_bp
from app.routes.user.user_settings import user_settings_bp

# Создаем главный blueprint для объединения всех user routes
user_routes_bp = Blueprint('user_routes', __name__)

# Регистрируем все под-blueprint'ы
user_routes_bp.register_blueprint(user_dashboard_bp)
user_routes_bp.register_blueprint(user_autopublish_bp)
user_routes_bp.register_blueprint(user_objects_bp)
user_routes_bp.register_blueprint(user_settings_bp)

