"""
Admin database schema routes
Логика: просмотр схемы БД и примеров данных из таблиц
"""
from flask import Blueprint, request, jsonify, render_template
from app.database import db
from app.utils.decorators import jwt_required, role_required
import logging

admin_database_schema_bp = Blueprint('admin_database_schema', __name__)
logger = logging.getLogger(__name__)


@admin_database_schema_bp.route('/dashboard/database-schema', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_database_schema_page(current_user):
    """Database schema viewer page"""
    return render_template('admin/database_schema.html', user=current_user)


@admin_database_schema_bp.route('/dashboard/database-schema/data', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_database_schema_data(current_user):
    """Get database schema information"""
    from sqlalchemy import inspect
    
    try:
        inspector = inspect(db.engine)
        schema_info = {}
        
        # Get all table names
        table_names = inspector.get_table_names()
        
        for table_name in table_names:
            table_info = {
                'name': table_name,
                'columns': [],
                'primary_keys': [],
                'foreign_keys': [],
                'indexes': []
            }
            
            # Get columns
            columns = inspector.get_columns(table_name)
            for col in columns:
                col_info = {
                    'name': col['name'],
                    'type': str(col['type']),
                    'nullable': col.get('nullable', True),
                    'default': str(col.get('default', 'None')),
                    'autoincrement': col.get('autoincrement', False)
                }
                table_info['columns'].append(col_info)
            
            # Get primary keys
            pk_constraint = inspector.get_pk_constraint(table_name)
            if pk_constraint:
                table_info['primary_keys'] = pk_constraint.get('constrained_columns', [])
            
            # Get foreign keys
            fks = inspector.get_foreign_keys(table_name)
            for fk in fks:
                fk_info = {
                    'constrained_columns': fk.get('constrained_columns', []),
                    'referred_table': fk.get('referred_table', ''),
                    'referred_columns': fk.get('referred_columns', [])
                }
                table_info['foreign_keys'].append(fk_info)
            
            # Get indexes
            indexes = inspector.get_indexes(table_name)
            for idx in indexes:
                idx_info = {
                    'name': idx.get('name', ''),
                    'columns': idx.get('column_names', []),
                    'unique': idx.get('unique', False)
                }
                table_info['indexes'].append(idx_info)
            
            schema_info[table_name] = table_info
        
        return jsonify({
            'success': True,
            'tables': schema_info,
            'table_count': len(table_names)
        })
    except Exception as e:
        logger.error(f"Error getting database schema: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_database_schema_bp.route('/dashboard/database-schema/examples', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_database_schema_examples(current_user):
    """Get 2 random example rows from selected table"""
    table_name = request.args.get('table')
    if not table_name:
        return jsonify({'error': 'table parameter is required'}), 400
    
    try:
        from sqlalchemy import text
        # Get 2 random rows from the table
        sql = text(f"""
            SELECT * FROM {table_name}
            ORDER BY RANDOM()
            LIMIT 2
        """)
        result_proxy = db.session.execute(sql)
        rows = result_proxy.fetchall()
        
        # Get column names - в SQLAlchemy 2.0+ используем keys() вместо description
        columns = list(result_proxy.keys())
        
        # Convert rows to dictionaries
        examples = []
        for row in rows:
            row_dict = {}
            for i, col_name in enumerate(columns):
                value = row[i]
                # Convert special types to JSON-serializable format
                if hasattr(value, 'isoformat'):  # datetime
                    value = value.isoformat()
                elif isinstance(value, (dict, list)):  # JSON fields
                    value = value
                elif value is None:
                    value = None
                else:
                    value = str(value)
                row_dict[col_name] = value
            examples.append(row_dict)
        
        return jsonify({
            'success': True,
            'table': table_name,
            'columns': columns,
            'examples': examples
        })
    except Exception as e:
        logger.error(f"Error getting examples from table {table_name}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

