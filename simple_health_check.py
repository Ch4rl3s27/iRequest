#!/usr/bin/env python3
"""
Simple Health Check for iRequest
Tests core functionality without complex dependency checking
"""

import os
import sys
from pathlib import Path

def test_application_startup():
    """Test if the application can start up"""
    try:
        print("🔍 Testing application startup...")
        
        # Add project root to Python path
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        
        from app import create_app
        app = create_app()
        
        print("✅ Application created successfully")
        
        # Test database connection
        with app.app_context():
            from app.models import db
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            print("✅ Database connection successful")
        
        print("✅ Application startup test passed")
        return True
        
    except Exception as e:
        print(f"❌ Application startup failed: {e}")
        return False

def test_environment():
    """Test environment configuration"""
    try:
        print("🔍 Testing environment configuration...")
        
        # Check if .env exists
        if not Path('.env').exists():
            print("❌ .env file not found")
            return False
        
        print("✅ .env file exists")
        
        # Check if main files exist
        required_files = ['main.py', 'config.py', 'app/__init__.py']
        for file_path in required_files:
            if not Path(file_path).exists():
                print(f"❌ Required file not found: {file_path}")
                return False
        
        print("✅ All required files exist")
        return True
        
    except Exception as e:
        print(f"❌ Environment test failed: {e}")
        return False

def main():
    """Run simple health check"""
    print("🔍 Running Simple Health Check...")
    print("=" * 50)
    
    tests = [
        ("Environment", test_environment),
        ("Application Startup", test_application_startup)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n🔍 Testing {name}...")
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error testing {name}: {e}")
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
        print("\n🎉 All tests passed! Your project is ready to run.")
        print("💡 You can now run: python main.py")
    else:
        print("\n⚠️ Some tests failed. Please check the issues above.")
    
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
