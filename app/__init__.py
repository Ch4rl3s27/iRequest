"""
iRequest Application Factory
Clean, modular Flask application
"""

import os
from flask import Flask
from flask_cors import CORS
from app.models import db
from app.routes import auth_bp, student_bp
from app.utils import setup_logging, log_info


def create_app(config_name: str = None) -> Flask:
    """
    Application factory
    
    Args:
        config_name: Configuration name (development, production, testing)
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Import and set configuration
    from config import config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    
    # Setup logging
    with app.app_context():
        setup_logging()
        log_info("Application initialized")
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(student_bp, url_prefix='/api')
    
    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            log_info("Database tables created successfully")
        except Exception as e:
            log_info(f"Database initialization warning: {e}")
    
    return app