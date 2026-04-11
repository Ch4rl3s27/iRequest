#!/usr/bin/env python3
"""
Script to drop unused student views from the database.
These views are no longer created by the application and can be safely removed.
"""

import os
import sys
from socket import gethostbyname, gaierror

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    print("❌ Error: pymysql is not installed. Please install it with: pip install pymysql")
    sys.exit(1)

# List of views to drop
VIEWS_TO_DROP = [
    # BEED views
    'BEED_Students_all',
    'BEED_Students_firstyear',
    'BEED_Students_secondyear',
    'BEED_Students_thirdyear',
    'BEED_Students_fourthyear',
    # BSED views
    'BSED_Students_all',
    'BSED_Students_firstyear',
    'BSED_Students_secondyear',
    'BSED_Students_thirdyear',
    'BSED_Students_fourthyear',
    # CS views
    'CS_Students_all',
    'CS_Students_firstyear',
    'CS_Students_secondyear',
    'CS_Students_thirdyear',
    'CS_Students_fourthyear',
    # HM views
    'HM_Students_all',
    'HM_Students_firstyear',
    'HM_Students_secondyear',
    'HM_Students_thirdyear',
    'HM_Students_fourthyear',
]

def get_db_connection():
    """Get database connection using the same logic as app.py"""
    use_local = os.getenv('USE_LOCAL_DB', '').lower() == 'true'
    env_host = os.getenv('MYSQL_HOST', 'irequest.cqv2smac4gvw.us-east-1.rds.amazonaws.com')
    env_user = os.getenv('MYSQL_USER', 'admin')
    env_pass = os.getenv('MYSQL_PASSWORD', 'Thesis_101')
    env_db = os.getenv('MYSQL_DB', 'irequest')
    
    if use_local:
        host = 'localhost'
        user = os.getenv('MYSQL_USER', 'root')
        password = os.getenv('MYSQL_PASSWORD', '')
        database = os.getenv('MYSQL_DB', 'irequest')
        print("🔧 Using LOCAL database configuration")
    else:
        try:
            _ = gethostbyname(env_host)
            host = env_host
            user = env_user
            password = env_pass
            database = env_db
            print("☁️ Using AWS RDS database configuration")
        except gaierror:
            print("❌ DNS resolution failed for configured DB host. Falling back to LOCAL DB.")
            host = 'localhost'
            user = os.getenv('MYSQL_USER', 'root')
            password = os.getenv('MYSQL_PASSWORD', '')
            database = os.getenv('MYSQL_DB', 'irequest')
    
    try:
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=DictCursor,
            autocommit=True,
            connect_timeout=10,
            read_timeout=60,
            write_timeout=60
        )
        print(f"✅ Connected to database: {database}")
        return connection
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        raise

def drop_views():
    """Drop all unused student views"""
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        dropped_count = 0
        not_found_count = 0
        
        print("\n🗑️  Starting to drop views...\n")
        
        for view_name in VIEWS_TO_DROP:
            try:
                # Check if view exists first
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.views 
                    WHERE table_schema = DATABASE() 
                    AND table_name = %s
                """, (view_name,))
                
                result = cursor.fetchone()
                if result and result['count'] > 0:
                    # Drop the view
                    cursor.execute(f"DROP VIEW IF EXISTS `{view_name}`")
                    print(f"✅ Dropped view: {view_name}")
                    dropped_count += 1
                else:
                    print(f"ℹ️  View not found (already removed): {view_name}")
                    not_found_count += 1
                    
            except Exception as e:
                print(f"⚠️  Error dropping view {view_name}: {e}")
        
        print(f"\n📊 Summary:")
        print(f"   ✅ Dropped: {dropped_count} views")
        print(f"   ℹ️  Not found: {not_found_count} views")
        print(f"   📝 Total checked: {len(VIEWS_TO_DROP)} views")
        
        if dropped_count > 0:
            print("\n✅ Successfully cleaned up unused views!")
        else:
            print("\nℹ️  No views were found to drop (they may have already been removed).")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("\n🔌 Database connection closed.")

if __name__ == '__main__':
    print("=" * 60)
    print("  Drop Unused Student Views Script")
    print("=" * 60)
    drop_views()

