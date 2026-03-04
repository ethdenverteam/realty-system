"""
Admin bot chats package
Логика: объединение всех bot chats blueprint'ов в один для регистрации в admin
"""
from flask import Blueprint

# Импортируем все blueprint'ы
from app.routes.admin.bot_chats.admin_bot_chats_list import admin_bot_chats_list_bp
from app.routes.admin.bot_chats.admin_bot_chats_crud import admin_bot_chats_crud_bp
from app.routes.admin.bot_chats.admin_bot_chats_config import admin_bot_chats_config_bp
from app.routes.admin.bot_chats.admin_bot_chats_publish import admin_bot_chats_publish_bp

# Создаем главный blueprint для объединения всех bot chats routes
admin_bot_chats_bp = Blueprint('admin_bot_chats', __name__)

# Регистрируем все под-blueprint'ы
admin_bot_chats_bp.register_blueprint(admin_bot_chats_list_bp)
admin_bot_chats_bp.register_blueprint(admin_bot_chats_crud_bp)
admin_bot_chats_bp.register_blueprint(admin_bot_chats_config_bp)
admin_bot_chats_bp.register_blueprint(admin_bot_chats_publish_bp)

