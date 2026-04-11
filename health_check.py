#!/usr/bin/env python3
"""
iRequest Health Check Script
Diagnoses and fixes common issues in the project
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required. Current version:", f"{version.major}.{version.minor}")
        return False
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        ('flask', 'flask'),
        ('flask-sqlalchemy', 'flask_sqlalchemy'),
        ('flask-mysqldb', 'flask_mysqldb'),
        ('pymysql', 'pymysql'),
        ('werkzeug', 'werkzeug'),
        ('requests', 'requests'),
        ('PyJWT', 'jwt'),
        ('Pillow', 'PIL'),
        ('boto3', 'boto3'),
        ('marshmallow', 'marshmallow'),
        ('flask-marshmallow', 'flask_marshmallow'),
        ('python-dotenv', 'dotenv'),
        ('flask-cors', 'flask_cors')
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("💡 Run: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies installed")
    return True

def check_file_structure():
    """Check if required files and directories exist"""
    required_files = [
        'main.py', 'config.py', 'requirements.txt',
        'app/__init__.py', 'app/models/__init__.py',
        'app/routes/__init__.py', 'app/services/__init__.py',
        'app/utils/__init__.py'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    
    print("✅ Project structure is correct")
    return True

def check_environment():
    """Check environment configuration"""
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found")
        print("💡 Run: python setup_environment.py")
        return False
    
    print("✅ Environment file exists")
    return True

def check_database_connection():
    """Test database connection"""
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.models import db
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def run_health_check():
    """Run complete health check"""
    print("🔍 Running iRequest Health Check...")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("File Structure", check_file_structure),
        ("Environment", check_environment),
        ("Database Connection", check_database_connection)
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n🔍 Checking {name}...")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error checking {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("📊 Health Check Results:")
    print("=" * 50)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All checks passed! Your project is healthy.")
        print("💡 You can now run: python main.py")
    else:
        print("\n⚠️ Some checks failed. Please fix the issues above.")
        print("💡 Try running: python setup_environment.py")
    
    return all_passed

if __name__ == '__main__':
    success = run_health_check()
    sys.exit(0 if success else 1)
