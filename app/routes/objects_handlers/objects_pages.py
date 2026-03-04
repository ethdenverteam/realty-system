"""
Objects pages routes
Логика: отображение страниц создания и списка объектов
"""
from flask import Blueprint, request, jsonify, current_app, render_template
from app.database import db
from app.models.object import Object
from app.utils.decorators import jwt_required, role_required
from app.utils.logger import log_action, log_error
from sqlalchemy import or_, and_
import logging

objects_pages_bp = Blueprint('objects_pages', __name__)
logger = logging.getLogger(__name__)

@objects_pages_bp.route('/create', methods=['GET'])
@jwt_required
def create_object_page(current_user):
    """Show object creation page"""
    return render_template('create_object.html')


@objects_pages_bp.route('/list', methods=['GET'])
@jwt_required
def list_objects_page(current_user):
    """Show objects list page"""
    return render_template('objects_list.html')

