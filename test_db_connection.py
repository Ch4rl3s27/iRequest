#!/usr/bin/env python3
"""
Database Connection Test Script
This script will help diagnose database connection issues
"""

import pymysql
import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Required tables for the application
REQUIRED_TABLES = ['students', 'staff', 'clearance_requests', 'clearance_signatories', 
                   'document_requests', 'auto_transfer_logs', 'document_files', 'clearance_files']

def test_database_connection():
    """Test database connection with detailed error reporting"""
    
    # Check environment variable
    use_local = os.getenv('USE_LOCAL_DB', '').lower() == 'true'
    
    if use_local:
        print("🔧 Testing LOCAL database connection...")
        config = {
            'host': 'localhost',
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DB', 'irequest'),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor,
            'autocommit': True,
            'connect_timeout': 10,
            'read_timeout': 30,
            'write_timeout': 30
        }
    else:
        print("☁️ Testing AWS RDS database connection...")
        config = {
            'host': os.getenv('MYSQL_HOST', 'irequest.cqv2smac4gvw.us-east-1.rds.amazonaws.com'),
            'user': os.getenv('MYSQL_USER', 'admin'),
            'password': os.getenv('MYSQL_PASSWORD', 'Thesis_101'),
            'database': os.getenv('MYSQL_DB', 'irequest'),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor,
            'autocommit': True,
            'connect_timeout': 10,
            'read_timeout': 30,
            'write_timeout': 30
        }
    
    print(f"🔍 Connection details:")
    print(f"   Host: {config['host']}")
    print(f"   Database: {config['database']}")
    print(f"   User: {config['user']}")
    print(f"   Password: {'*' * len(config['password']) if config['password'] else '(empty)'}")
    
    try:
        print("\n🔍 Attempting to connect...")
        connection = pymysql.connect(**config)
        print("✅ Database connection successful!")
        
        # Test basic query
        print("\n🔍 Testing basic query...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ MySQL Version: {version['VERSION()']}")
            
            # Get all existing tables
            print("\n🔍 Checking database tables...")
            cursor.execute("SHOW TABLES")
            existing_tables = [list(row.values())[0] for row in cursor.fetchall()]
            print(f"📊 Found {len(existing_tables)} tables: {', '.join(sorted(existing_tables))}")
            
            # Check required tables
            print("\n🔍 Verifying required tables...")
            missing_tables = []
            for table in REQUIRED_TABLES:
                if table in existing_tables:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    count = cursor.fetchone()['count']
                    print(f"   ✅ {table} - exists ({count} records)")
                else:
                    print(f"   ❌ {table} - MISSING")
                    missing_tables.append(table)
            
            if missing_tables:
                print(f"\n⚠️  Missing {len(missing_tables)} required table(s): {', '.join(missing_tables)}")
                print("💡 Solution: Run your Flask application - it will automatically create missing tables.")
            else:
                print("\n✅ All required tables are present!")
        
        connection.close()
        if missing_tables:
            print("\n⚠️  Database connection works, but some tables are missing.")
            return False
        else:
            print("\n✅ All tests passed!")
            return True
        
    except pymysql.Error as e:
        print(f"\n❌ PyMySQL Error: {e}")
        print(f"   Error Code: {e.args[0]}")
        print(f"   Error Message: {e.args[1]}")
        
        # Common error codes and solutions
        if e.args[0] == 2003:
            print("\n💡 Solution: Check if MySQL server is running")
            if use_local:
                print("   - Start MySQL service: net start mysql (Windows) or sudo service mysql start (Linux)")
        elif e.args[0] == 1045:
            print("\n💡 Solution: Check username and password")
        elif e.args[0] == 1049:
            print("\n💡 Solution: Database 'irequest' does not exist")
            print("   - Create database: CREATE DATABASE irequest;")
        elif e.args[0] == 2002:
            print("\n💡 Solution: Cannot connect to MySQL server")
            if not use_local:
                print("   - Check AWS RDS security groups")
                print("   - Verify RDS instance is running")
        
        return False
        
    except Exception as e:
        print(f"\n❌ General Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE CONNECTION TEST")
    print("=" * 60)
    
    success = test_database_connection()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ DATABASE CONNECTION TEST PASSED")
        print("Your Flask app should work now!")
    else:
        print("❌ DATABASE CONNECTION TEST FAILED")
        print("Please fix the issues above before running your Flask app")
    print("=" * 60)
