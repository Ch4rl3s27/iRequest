#!/usr/bin/env python3
"""
Database Connection Test Script
This script will help diagnose database connection issues
"""

import pymysql
import os

def test_database_connection():
    """Test database connection with detailed error reporting"""
    
    # Check environment variable
    use_local = os.getenv('USE_LOCAL_DB', '').lower() == 'true'
    
    if use_local:
        print("🔧 Testing LOCAL database connection...")
        config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'irequest',
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
            'host': 'irequest.ctyeeiou09cg.ap-southeast-2.rds.amazonaws.com',
            'user': 'admin',
            'password': 'Thesis_101',
            'database': 'irequest',
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
            
            # Test clearance_requests table
            cursor.execute("SHOW TABLES LIKE 'clearance_requests'")
            table_exists = cursor.fetchone()
            if table_exists:
                print("✅ clearance_requests table exists")
                
                # Test columns
                cursor.execute("SHOW COLUMNS FROM clearance_requests")
                columns = [row['Field'] for row in cursor.fetchall()]
                print(f"✅ Available columns: {columns}")
                
                # Test data
                cursor.execute("SELECT COUNT(*) as count FROM clearance_requests")
                count = cursor.fetchone()
                print(f"✅ Record count: {count['count']}")
                
                # Test specific record
                cursor.execute("SELECT id, student_id, payment_receipt FROM clearance_requests WHERE id = 85")
                record = cursor.fetchone()
                if record:
                    print(f"✅ Record 85 found: ID={record['id']}, Student ID={record['student_id']}")
                    print(f"✅ Payment receipt: {'Present' if record['payment_receipt'] else 'NULL'}")
                else:
                    print("❌ Record 85 not found")
            else:
                print("❌ clearance_requests table does not exist")
        
        connection.close()
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
