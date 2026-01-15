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
    app = Flask(__name__, template_folder=template_dir)
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
        import traceback
        
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
    from app.routes.admin import admin_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.logs import logs_bp
    from app.routes.logs_viewer import logs_viewer_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(objects_bp, url_prefix='/api/objects')
    app.register_blueprint(accounts_bp, url_prefix='/api/accounts')
    app.register_blueprint(chats_bp, url_prefix='/api/chats')
    app.register_blueprint(publications_bp, url_prefix='/api/publications')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(logs_bp, url_prefix='/api/logs')
    app.register_blueprint(logs_viewer_bp, url_prefix='/api/logs-viewer')
    
    # Web pages
    @app.route('/')
    def index():
        """Redirect to login"""
        from flask import redirect
        return redirect('/api/auth/login')
    
    @app.route('/dashboard')
    def dashboard_page():
        """Dashboard page"""
        from flask import render_template
        return render_template('dashboard.html')
    
    # Initialize database
    with app.app_context():
        init_db()
    
    return app


# Create app instance for Gunicorn
app = create_app()
