"""
Admin bot chats publish routes
Логика: тестовая публикация и публикация объектов в чаты
"""
from flask import Blueprint, request, jsonify, render_template
from app.database import db
from app.models.user import User
from app.models.object import Object
from app.models.chat import Chat
from app.models.telegram_account_chat import TelegramAccountChat
from app.models.chat_group import ChatGroup
from app.models.action_log import ActionLog
from app.utils.decorators import jwt_required, role_required
from app.utils.logger import log_action, log_error
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import logging

admin_bot_chats_publish_bp = Blueprint('admin_bot_chats_publish', __name__)
logger = logging.getLogger(__name__)


