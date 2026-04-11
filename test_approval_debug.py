#!/usr/bin/env python3
"""
Test script to debug the approval process
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from the root app.py file, not the app package
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the create_app function from the root app.py
import importlib.util
spec = importlib.util.spec_from_file_location("app_module", "app.py")
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
create_app = app_module.create_app

def test_database_connection():
    """Test if database connection is working"""
    try:
        app = create_app()
        with app.app_context():
            # Import mysql from the main app module
            import app
            mysql = app.mysql
            cur, conn = mysql.cursor()
            cur.execute("SELECT 1")
            result = cur.fetchone()
            cur.close()
            conn.close()
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_clearance_signatories_table():
    """Test if clearance_signatories table exists and has data"""
    try:
        app = create_app()
        with app.app_context():
            mysql = app_module.mysql
            cur, conn = mysql.cursor()
            
            # Check if table exists
            cur.execute("SHOW TABLES LIKE 'clearance_signatories'")
            table_exists = cur.fetchone()
            if not table_exists:
                print("❌ clearance_signatories table does not exist")
                return False
            
            # Check table structure
            cur.execute("DESCRIBE clearance_signatories")
            columns = cur.fetchall()
            print("📋 clearance_signatories table structure:")
            for col in columns:
                print(f"  - {col['Field']}: {col['Type']}")
            
            # Check for sample data
            cur.execute("SELECT COUNT(*) as count FROM clearance_signatories")
            count = cur.fetchone()['count']
            print(f"📊 Total signatories: {count}")
            
            if count > 0:
                # Get a sample record
                cur.execute("SELECT * FROM clearance_signatories LIMIT 1")
                sample = cur.fetchone()
                print(f"📝 Sample record: {sample}")
            
            cur.close()
            conn.close()
            return True
    except Exception as e:
        print(f"❌ Error checking clearance_signatories table: {e}")
        return False

def test_clearance_requests_table():
    """Test if clearance_requests table exists and has data"""
    try:
        app = create_app()
        with app.app_context():
            mysql = app_module.mysql
            cur, conn = mysql.cursor()
            
            # Check if table exists
            cur.execute("SHOW TABLES LIKE 'clearance_requests'")
            table_exists = cur.fetchone()
            if not table_exists:
                print("❌ clearance_requests table does not exist")
                return False
            
            # Check table structure
            cur.execute("DESCRIBE clearance_requests")
            columns = cur.fetchall()
            print("📋 clearance_requests table structure:")
            for col in columns:
                print(f"  - {col['Field']}: {col['Type']}")
            
            # Check for sample data
            cur.execute("SELECT COUNT(*) as count FROM clearance_requests")
            count = cur.fetchone()['count']
            print(f"📊 Total clearance requests: {count}")
            
            if count > 0:
                # Get a sample record
                cur.execute("SELECT * FROM clearance_requests LIMIT 1")
                sample = cur.fetchone()
                print(f"📝 Sample record: {sample}")
            
            cur.close()
            conn.close()
            return True
    except Exception as e:
        print(f"❌ Error checking clearance_requests table: {e}")
        return False

def test_staff_table():
    """Test if staff table exists and has data"""
    try:
        app = create_app()
        with app.app_context():
            mysql = app_module.mysql
            cur, conn = mysql.cursor()
            
            # Check if table exists
            cur.execute("SHOW TABLES LIKE 'staff'")
            table_exists = cur.fetchone()
            if not table_exists:
                print("❌ staff table does not exist")
                return False
            
            # Check for sample data
            cur.execute("SELECT COUNT(*) as count FROM staff WHERE status = 'Approved'")
            count = cur.fetchone()['count']
            print(f"📊 Total approved staff: {count}")
            
            if count > 0:
                # Get a sample record
                cur.execute("SELECT id, first_name, last_name, email, department FROM staff WHERE status = 'Approved' LIMIT 1")
                sample = cur.fetchone()
                print(f"📝 Sample staff record: {sample}")
            
            cur.close()
            conn.close()
            return True
    except Exception as e:
        print(f"❌ Error checking staff table: {e}")
        return False

def main():
    print("🔍 Testing approval system components...")
    print("=" * 50)
    
    # Test database connection
    print("\n1. Testing database connection...")
    if not test_database_connection():
        print("❌ Cannot proceed without database connection")
        return
    
    # Test tables
    print("\n2. Testing clearance_signatories table...")
    test_clearance_signatories_table()
    
    print("\n3. Testing clearance_requests table...")
    test_clearance_requests_table()
    
    print("\n4. Testing staff table...")
    test_staff_table()
    
    print("\n" + "=" * 50)
    print("✅ Debug test completed!")

if __name__ == "__main__":
    main()
