"""
Flask application factory
"""
from flask import Flask
from flask_cors import CORS
from app.database import db, init_db
from app.config import Config


def create_app(config_class=Config):
    """Create and configure Flask application"""
    import os
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    app = Flask(__name__, template_folder=template_dir)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.objects import objects_bp
    from app.routes.accounts import accounts_bp
    from app.routes.chats import chats_bp
    from app.routes.publications import publications_bp
    from app.routes.admin import admin_bp
    from app.routes.dashboard import dashboard_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(objects_bp, url_prefix='/api/objects')
    app.register_blueprint(accounts_bp, url_prefix='/api/accounts')
    app.register_blueprint(chats_bp, url_prefix='/api/chats')
    app.register_blueprint(publications_bp, url_prefix='/api/publications')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    
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
