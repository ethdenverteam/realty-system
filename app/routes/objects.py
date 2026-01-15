"""
Objects routes
"""
from flask import Blueprint, request, jsonify, current_app, render_template
from app.database import db
from app.models.object import Object
from app.utils.decorators import jwt_required, role_required
from app.utils.logger import log_action, log_error
from sqlalchemy import or_, and_
import logging

objects_bp = Blueprint('objects', __name__)
logger = logging.getLogger(__name__)


@objects_bp.route('/create', methods=['GET'])
@jwt_required
def create_object_page(current_user):
    """Show object creation page"""
    return render_template('create_object.html')


@objects_bp.route('/', methods=['GET'])
@jwt_required
def list_objects(current_user):
    """Get list of objects"""
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    rooms_type = request.args.get('rooms_type')
    search = request.args.get('search')
    sort_by = request.args.get('sort_by', 'creation_date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Build query
    query = Object.query.filter_by(user_id=current_user.user_id)
    
    # Apply filters
    if status:
        query = query.filter(Object.status == status)
    
    if rooms_type:
        query = query.filter(Object.rooms_type == rooms_type)
    
    if search:
        search_filter = or_(
            Object.object_id.ilike(f'%{search}%'),
            Object.address.ilike(f'%{search}%'),
            Object.comment.ilike(f'%{search}%')
        )
        query = query.filter(search_filter)
    
    # Apply sorting
    if sort_by == 'price':
        order_by = Object.price.desc() if sort_order == 'desc' else Object.price.asc()
    elif sort_by == 'publication_date':
        order_by = Object.publication_date.desc() if sort_order == 'desc' else Object.publication_date.asc()
    else:  # creation_date
        order_by = Object.creation_date.desc() if sort_order == 'desc' else Object.creation_date.asc()
    
    query = query.order_by(order_by)
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'objects': [obj.to_dict() for obj in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })


@objects_bp.route('/<object_id>', methods=['GET'])
@jwt_required
def get_object(object_id, current_user):
    """Get single object"""
    obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
    
    if not obj:
        return jsonify({'error': 'Object not found'}), 404
    
    return jsonify(obj.to_dict())


@objects_bp.route('/', methods=['POST'])
@jwt_required
def create_object(current_user):
    """Create new object"""
    from werkzeug.utils import secure_filename
    import os
    import json
    
    # Check if form data (file upload) or JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Handle form data with file uploads
        rooms_type = request.form.get('rooms_type', '')
        price = float(request.form.get('price', 0))
        area = float(request.form.get('area', 0)) if request.form.get('area') else None
        floor = request.form.get('floor', '')
        comment = request.form.get('comment', '')
        address = request.form.get('address', '')
        renovation = request.form.get('renovation', '')
        contact_name = request.form.get('contact_name', '')
        phone_number = request.form.get('phone_number', '')
        show_username = request.form.get('show_username') == 'true'
        
        # Parse districts
        districts_json_str = request.form.get('districts_json', '[]')
        try:
            districts_json = json.loads(districts_json_str) if districts_json_str else []
        except:
            districts_json = []
        
        # Handle photo uploads
        photos_json = []
        photo_index = 0
        while f'photo_{photo_index}' in request.files:
            file = request.files[f'photo_{photo_index}']
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Create unique filename
                from datetime import datetime
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                file.save(filepath)
                photos_json.append(f"uploads/{filename}")
            photo_index += 1
    else:
        # Handle JSON data
        data = request.get_json()
        rooms_type = data.get('rooms_type', '')
        price = float(data.get('price', 0))
        area = data.get('area')
        floor = data.get('floor', '')
        comment = data.get('comment', '')
        address = data.get('address', '')
        renovation = data.get('renovation', '')
        contact_name = data.get('contact_name', '')
        phone_number = data.get('phone_number', '')
        show_username = data.get('show_username', False)
        districts_json = data.get('districts_json', [])
        photos_json = data.get('photos_json', [])
    
    # Generate object_id (proper logic from bot)
    prefix = current_user.settings_json.get('id_prefix', 'WEB') if current_user.settings_json else 'WEB'
    if not prefix:
        # Generate prefix if not exists
        from bot.utils import generate_next_id_prefix
        prefix = generate_next_id_prefix()
        if not current_user.settings_json:
            current_user.settings_json = {}
        current_user.settings_json['id_prefix'] = prefix
        db.session.commit()
    
    # Get next number for user
    last_obj = Object.query.filter(
        Object.object_id.like(f'{prefix}%')
    ).order_by(Object.object_id.desc()).first()
    
    if last_obj:
        try:
            num = int(last_obj.object_id[len(prefix):]) + 1
        except:
            num = 1
    else:
        num = 1
    
    object_id = f"{prefix}{num:03d}"
    
    # Create object
    obj = Object(
        object_id=object_id,
        user_id=current_user.user_id,
        rooms_type=rooms_type,
        price=price,
        districts_json=districts_json,
        region=None,  # TODO: Extract from districts
        city=None,  # TODO: Extract from districts
        photos_json=photos_json,
        area=area,
        floor=floor,
        address=address,
        renovation=renovation,
        comment=comment,
        contact_name=contact_name,
        show_username=show_username,
        phone_number=phone_number,
        status='черновик',
        source='web'
    )
    
    try:
        db.session.add(obj)
        db.session.commit()
        
        # Log creation
        log_action(
            action='object_created',
            user_id=current_user.user_id,
            details={
                'object_id': object_id,
                'rooms_type': obj.rooms_type,
                'price': obj.price,
                'status': obj.status,
                'source': 'web'
            }
        )
        
        return jsonify(obj.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        log_error(e, 'object_create_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({'error': str(e)}), 500


@objects_bp.route('/<object_id>', methods=['PUT'])
@jwt_required
def update_object(object_id, current_user):
    """Update object"""
    obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
    
    if not obj:
        return jsonify({'error': 'Object not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if 'rooms_type' in data:
        obj.rooms_type = data['rooms_type']
    if 'price' in data:
        obj.price = float(data['price'])
    if 'districts_json' in data:
        obj.districts_json = data['districts_json']
    if 'photos_json' in data:
        obj.photos_json = data['photos_json']
    if 'area' in data:
        obj.area = data['area']
    if 'floor' in data:
        obj.floor = data['floor']
    if 'address' in data:
        obj.address = data['address']
    if 'renovation' in data:
        obj.renovation = data['renovation']
    if 'comment' in data:
        obj.comment = data['comment']
    if 'contact_name' in data:
        obj.contact_name = data['contact_name']
    if 'show_username' in data:
        obj.show_username = data['show_username']
    if 'phone_number' in data:
        obj.phone_number = data['phone_number']
    if 'status' in data:
        obj.status = data['status']
    
    try:
        # Store old status for logging
        old_status = obj.status
        db.session.commit()
        
        # Log update
        log_action(
            action='object_updated',
            user_id=current_user.user_id,
            details={
                'object_id': object_id,
                'updated_fields': list(data.keys()),
                'old_status': old_status if 'status' in data else None,
                'new_status': obj.status if 'status' in data else None
            }
        )
        
        return jsonify(obj.to_dict())
    except Exception as e:
        db.session.rollback()
        log_error(e, 'object_update_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({'error': str(e)}), 500


@objects_bp.route('/<object_id>', methods=['DELETE'])
@jwt_required
def delete_object(object_id, current_user):
    """Delete object"""
    obj = Object.query.filter_by(object_id=object_id, user_id=current_user.user_id).first()
    
    if not obj:
        return jsonify({'error': 'Object not found'}), 404
    
    try:
        # Store object info for logging
        object_info = {
            'object_id': object_id,
            'rooms_type': obj.rooms_type,
            'price': obj.price,
            'status': obj.status
        }
        
        db.session.delete(obj)
        db.session.commit()
        
        # Log deletion
        log_action(
            action='object_deleted',
            user_id=current_user.user_id,
            details=object_info
        )
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        log_error(e, 'object_delete_failed', current_user.user_id, {'object_id': object_id})
        return jsonify({'error': str(e)}), 500

