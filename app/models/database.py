"""
Database initialization and connection utilities
"""

import os
from typing import Any, cast

def init_db() -> None:
    """Initialize database tables and structures"""
    mysql = get_db_connection()
    
    if mysql is None:
        print("⚠️ Database not available - skipping initialization")
        return
    
    try:
        cur = mysql.connection.cursor()
        
        # Create tables if they don't exist
        create_tables(cur)
        
        mysql.connection.commit()
        cur.close()
        print("✅ Database tables initialized successfully")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

def create_tables(cursor):
    """Create all necessary database tables"""
    
    # Students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(20) UNIQUE NOT NULL,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            otp_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Staff table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            department VARCHAR(100) NOT NULL,
            status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Clearance requests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clearance_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            request_type VARCHAR(100) NOT NULL,
            status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
            payment_receipt LONGTEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)
    
    # Notifications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            staff_name VARCHAR(200) NOT NULL,
            action VARCHAR(100) NOT NULL,
            phase VARCHAR(100) NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

def get_db_connection():
    """Get database connection"""
    try:
        # Import the main app module to get mysql connection
        import sys
        import os
        parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.insert(0, parent_dir)
        
        import app
        return app.mysql
    except Exception as e:
        print(f"⚠️ Could not get database connection: {e}")
        return None
