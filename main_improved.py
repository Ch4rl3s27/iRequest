"""
Main application entry point
Clean, optimized Flask application with proper error handling
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from app import create_app
    from app.utils import log_info, log_error
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

def main():
    """Main application entry point"""
    print("=" * 50)
    print("🚀 Starting iRequest Application")
    print("=" * 50)
    
    try:
        # Create the application
        app = create_app()
        
        # Test database connection
        with app.app_context():
            from app.models import db
            try:
                # Test database connection
                db.session.execute('SELECT 1')
                log_info("✅ Database connection available")
            except Exception as e:
                log_error("❌ Database connection error", e)
                print(f"❌ Database connection error: {e}")
                print("💡 Try running: python setup_environment.py")
                return False
        
        # Run the application
        debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 'on']
        print(f"🌐 Starting server on http://localhost:5000")
        print(f"🔧 Debug mode: {'ON' if debug_mode else 'OFF'}")
        
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=debug_mode
        )
        
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        return False

if __name__ == '__main__':
    success = main()
    if not success:
        sys.exit(1)
