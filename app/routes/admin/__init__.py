"""
Admin routes package
Логика: объединение всех admin blueprint'ов в один для регистрации в app
"""
from flask import Blueprint

# Импортируем все blueprint'ы
from app.routes.admin.admin_dashboard import admin_dashboard_bp
from app.routes.admin.admin_database_schema import admin_database_schema_bp
from app.routes.admin.admin_users import admin_users_bp
from app.routes.admin.admin_logs import admin_logs_bp
from app.routes.admin.admin_settings import admin_settings_bp
from app.routes.admin.admin_chat_lists import admin_chat_lists_bp

# Создаем главный blueprint для объединения всех admin routes
admin_routes_bp = Blueprint('admin_routes', __name__)

# Регистрируем все под-blueprint'ы
admin_routes_bp.register_blueprint(admin_dashboard_bp)
admin_routes_bp.register_blueprint(admin_database_schema_bp)
admin_routes_bp.register_blueprint(admin_users_bp)
admin_routes_bp.register_blueprint(admin_logs_bp)
admin_routes_bp.register_blueprint(admin_settings_bp)
admin_routes_bp.register_blueprint(admin_chat_lists_bp)

# TODO: Добавить остальные модули после их создания:
# - admin_bot_chats_bp (bot chats management)
# - admin_publication_queues_bp (publication queues monitoring)
# - admin_account_autopublish_bp (account autopublish monitoring)

