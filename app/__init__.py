"""
Flask application factory
"""
import logging
from flask import Flask, g
from flask_cors import CORS
from app.database import db, init_db
from app.config import Config
from app.utils.logger import setup_logging, log_request, log_response


def create_app(config_class=Config):
    """Create and configure Flask application"""
    import os
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(config_class)
    
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Initializing Flask application...")
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    
    # Request logging middleware
    @app.before_request
    def before_request():
        log_request()
    
    @app.after_request
    def after_request(response):
        return log_response(response)
    
    # Error handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        from app.utils.logger import log_error
        from werkzeug.exceptions import NotFound
        import traceback
        
        # Don't log 404 errors for /metrics (Prometheus)
        from flask import request
        if isinstance(e, NotFound) and request.path == '/metrics':
            from flask import jsonify
            return jsonify({'error': 'Not found'}), 404
        
        logger = logging.getLogger('app.errors')
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        
        # Log to database
        user_id = None
        if hasattr(g, 'current_user') and g.current_user:
            user_id = g.current_user.user_id
        
        log_error(
            error=e,
            action='unhandled_exception',
            user_id=user_id,
            details={'traceback': traceback.format_exc()}
        )
        
        # Return error response
        from flask import jsonify
        return jsonify({
            'error': 'Internal server error',
            'message': str(e) if app.config.get('FLASK_ENV') == 'development' else 'An error occurred'
        }), 500
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.objects import objects_bp
    from app.routes.accounts import accounts_bp
    from app.routes.chats import chats_bp
    from app.routes.publications import publications_bp
    from app.routes.admin import admin_bp  # Legacy, keep for backward compatibility
    from app.routes.dashboard import dashboard_bp  # Legacy
    from app.routes.logs import logs_bp  # Legacy
    from app.routes.logs_viewer import logs_viewer_bp  # Legacy
    from app.routes.admin_routes import admin_routes_bp
    from app.routes.user_routes import user_routes_bp
    
    # New structure
    app.register_blueprint(admin_routes_bp, url_prefix='/system/admin')
    app.register_blueprint(user_routes_bp, url_prefix='/system/user')
    
    # Legacy routes (keep for backward compatibility)
    app.register_blueprint(auth_bp, url_prefix='/system/auth')
    app.register_blueprint(objects_bp, url_prefix='/system/objects')
    app.register_blueprint(accounts_bp, url_prefix='/system/accounts')
    app.register_blueprint(chats_bp, url_prefix='/system/chats')
    app.register_blueprint(publications_bp, url_prefix='/system/publications')
    app.register_blueprint(admin_bp, url_prefix='/system/admin/legacy')
    app.register_blueprint(dashboard_bp, url_prefix='/system/dashboard/legacy')
    app.register_blueprint(logs_bp, url_prefix='/system/logs/legacy')
    app.register_blueprint(logs_viewer_bp, url_prefix='/system/logs-viewer/legacy')
    # Also register for /api/logs for frontend compatibility with unique name
    from flask import Blueprint
    from app.routes.logs_viewer import stream_logs, list_log_files, view_logs_page
    
    logs_viewer_api_bp = Blueprint('logs_viewer_api', __name__)
    from app.routes.logs_viewer import download_logs, download_log_file
    logs_viewer_api_bp.add_url_rule('/stream', 'stream_logs', stream_logs, methods=['GET'])
    logs_viewer_api_bp.add_url_rule('/files', 'list_log_files', list_log_files, methods=['GET'])
    logs_viewer_api_bp.add_url_rule('/view', 'view_logs_page', view_logs_page, methods=['GET'])
    logs_viewer_api_bp.add_url_rule('/download', 'download_logs', download_logs, methods=['GET'])
    logs_viewer_api_bp.add_url_rule('/file/<log_type>', 'download_log_file', download_log_file, methods=['GET'])
    app.register_blueprint(logs_viewer_api_bp, url_prefix='/api/logs')
    
    # Serve React app static files (must be last to catch all non-API routes)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react_app(path):
        """Serve React app for all routes"""
        import os
        from flask import send_from_directory
        from werkzeug.exceptions import NotFound
        
        # If path is an API route, let it pass through (should be handled by blueprints above)
        if path.startswith('system/'):
            raise NotFound()
        
        # Serve static files
        static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
        
        # If path is a static asset (JS, CSS, images), serve it
        if path and not path.endswith('/'):
            # Check if it's a static file
            static_file = os.path.join(static_folder, path)
            if os.path.exists(static_file) and os.path.isfile(static_file):
                return send_from_directory(static_folder, path)
        
        # Otherwise serve index.html for React Router (SPA routing)
        index_file = os.path.join(static_folder, 'index.html')
        if os.path.exists(index_file):
            return send_from_directory(static_folder, 'index.html')
        
        # Fallback - redirect to login (if static files not built yet)
        from flask import redirect
        return redirect('/system/auth/login')
    
    # Initialize database
    with app.app_context():
        init_db()
    
    return app


# Create app instance for Gunicorn
app = create_app()
