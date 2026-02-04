#!/usr/bin/env python3
"""
Migration Script: Add missing columns to clearance_signatories table
This script adds signed_by and signed_at columns if they don't exist
"""

import pymysql
import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def get_db_config():
    """Get database configuration from environment"""
    use_local = os.getenv('USE_LOCAL_DB', '').lower() == 'true'
    
    if use_local:
        return {
            'host': 'localhost',
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DB', 'irequest'),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor,
            'autocommit': True,
        }
    else:
        return {
            'host': os.getenv('MYSQL_HOST'),
            'user': os.getenv('MYSQL_USER'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DB', 'irequest'),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor,
            'autocommit': True,
        }

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"""
        SELECT COUNT(*) as count 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = %s 
        AND COLUMN_NAME = %s
    """, (table_name, column_name))
    result = cursor.fetchone()
    return result['count'] > 0

def migrate_clearance_signatories():
    """Add missing columns to clearance_signatories table"""
    config = get_db_config()
    
    print("🔍 Starting migration for clearance_signatories table...")
    print(f"   Host: {config['host']}")
    print(f"   Database: {config['database']}")
    
    try:
        connection = pymysql.connect(**config)
        print("✅ Database connection successful!")
        
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'clearance_signatories'")
            if not cursor.fetchone():
                print("❌ Table 'clearance_signatories' does not exist!")
                print("💡 Run your Flask app first to create the table.")
                return False
            
            print("✅ Table 'clearance_signatories' exists")
            
            # Check and add signed_by column
            if check_column_exists(cursor, 'clearance_signatories', 'signed_by'):
                print("✅ Column 'signed_by' already exists")
            else:
                print("🔧 Adding column 'signed_by'...")
                cursor.execute("ALTER TABLE clearance_signatories ADD COLUMN signed_by VARCHAR(255) NULL")
                print("✅ Successfully added 'signed_by' column")
            
            # Check and add signed_at column
            if check_column_exists(cursor, 'clearance_signatories', 'signed_at'):
                print("✅ Column 'signed_at' already exists")
            else:
                print("🔧 Adding column 'signed_at'...")
                cursor.execute("ALTER TABLE clearance_signatories ADD COLUMN signed_at TIMESTAMP NULL")
                print("✅ Successfully added 'signed_at' column")
            
            # Verify the columns
            print("\n🔍 Verifying table structure...")
            cursor.execute("DESCRIBE clearance_signatories")
            columns = cursor.fetchall()
            column_names = [col['Field'] for col in columns]
            
            if 'signed_by' in column_names and 'signed_at' in column_names:
                print("✅ Migration completed successfully!")
                print("\n📋 Current columns in clearance_signatories:")
                for col in columns:
                    print(f"   - {col['Field']}: {col['Type']}")
                return True
            else:
                print("❌ Migration failed - columns not found after migration")
                return False
        
        connection.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add missing columns to clearance_signatories")
    print("=" * 60)
    success = migrate_clearance_signatories()
    print("=" * 60)
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed. Please check the errors above.")
    print("=" * 60)
