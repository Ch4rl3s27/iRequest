#!/usr/bin/env python3
"""
Database Tables Verification Script
Checks if all required tables exist in the database
"""

import pymysql
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Required tables for the application
REQUIRED_TABLES = {
    'students': ['id', 'student_no', 'first_name', 'last_name', 'email', 'password_hash'],
    'staff': ['id', 'department', 'first_name', 'last_name', 'email', 'password_hash', 'status'],
    'clearance_requests': ['id', 'student_id', 'status', 'document_type', 'created_at'],
    'clearance_signatories': ['id', 'request_id', 'office', 'status'],
    'document_requests': ['id', 'student_id', 'document_type', 'status', 'created_at'],
    'auto_transfer_logs': ['id', 'clearance_request_id', 'document_request_id', 'student_id'],
    'document_files': ['id', 'document_request_id', 'original_name', 'file_path'],
    'clearance_files': ['id', 'clearance_request_id', 'original_name', 'file_path']
}

def get_db_config():
    """Get database configuration from environment"""
    use_local = os.getenv('USE_LOCAL_DB', '').lower() == 'true'
    
    if use_local:
        return {
            'host': 'localhost',
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DB', 'irequest'),
        }
    else:
        return {
            'host': os.getenv('MYSQL_HOST'),
            'user': os.getenv('MYSQL_USER'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DB', 'irequest'),
        }

def verify_database_tables():
    """Verify all required database tables exist"""
    
    config = get_db_config()
    
    print("=" * 70)
    print("DATABASE TABLES VERIFICATION")
    print("=" * 70)
    print(f"\n🔍 Connecting to database...")
    print(f"   Host: {config['host']}")
    print(f"   Database: {config['database']}")
    print(f"   User: {config['user']}")
    
    try:
        connection = pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10
        )
        
        print("✅ Database connection successful!\n")
        
        with connection.cursor() as cursor:
            # Get all existing tables
            cursor.execute("SHOW TABLES")
            existing_tables = [list(row.values())[0] for row in cursor.fetchall()]
            
            print(f"📊 Found {len(existing_tables)} tables in database:")
            for table in sorted(existing_tables):
                print(f"   - {table}")
            
            print("\n" + "=" * 70)
            print("VERIFYING REQUIRED TABLES")
            print("=" * 70 + "\n")
            
            missing_tables = []
            tables_with_issues = []
            all_good = True
            
            for table_name, required_columns in REQUIRED_TABLES.items():
                print(f"🔍 Checking table: {table_name}")
                
                if table_name not in existing_tables:
                    print(f"   ❌ MISSING - Table '{table_name}' does not exist!")
                    missing_tables.append(table_name)
                    all_good = False
                else:
                    # Check columns
                    cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                    existing_columns = [row['Field'] for row in cursor.fetchall()]
                    
                    missing_columns = [col for col in required_columns if col not in existing_columns]
                    
                    if missing_columns:
                        print(f"   ⚠️  PARTIAL - Missing columns: {', '.join(missing_columns)}")
                        tables_with_issues.append((table_name, missing_columns))
                        all_good = False
                    else:
                        # Count records
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                        count = cursor.fetchone()['count']
                        print(f"   ✅ OK - All required columns present ({count} records)")
            
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            
            if all_good:
                print("\n✅ ALL REQUIRED TABLES ARE PRESENT AND CORRECT!")
                print("   Your database is ready to use.")
            else:
                print("\n⚠️  ISSUES FOUND:")
                
                if missing_tables:
                    print(f"\n❌ Missing Tables ({len(missing_tables)}):")
                    for table in missing_tables:
                        print(f"   - {table}")
                    print("\n💡 Solution: Run your Flask application - it will automatically create missing tables.")
                
                if tables_with_issues:
                    print(f"\n⚠️  Tables with Missing Columns ({len(tables_with_issues)}):")
                    for table, columns in tables_with_issues:
                        print(f"   - {table}: {', '.join(columns)}")
                    print("\n💡 Solution: The application will add missing columns automatically on startup.")
            
            print("\n" + "=" * 70)
        
        connection.close()
        return all_good
        
    except pymysql.Error as e:
        print(f"\n❌ Database Error: {e}")
        print(f"   Error Code: {e.args[0]}")
        print(f"   Error Message: {e.args[1]}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = verify_database_tables()
    exit(0 if success else 1)
