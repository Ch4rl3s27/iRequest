#!/usr/bin/env python3
"""
Environment Setup Script
This script helps set up the environment for local development
"""

import os
import sys

def setup_environment():
    """Set up environment variables for local development"""
    
    print("🔧 Setting up environment for local development...")
    
    # Set environment variable for local database
    os.environ['USE_LOCAL_DB'] = 'true'
    
    print("✅ Environment variable USE_LOCAL_DB set to 'true'")
    print("✅ This will use local MySQL database instead of AWS RDS")
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("\n📝 Creating .env file...")
        with open('.env', 'w') as f:
            f.write("# iRequest Environment Configuration\n")
            f.write("USE_LOCAL_DB=true\n")
            f.write("\n# Database Configuration\n")
            f.write("MYSQL_HOST=localhost\n")
            f.write("MYSQL_USER=root\n")
            f.write("MYSQL_PASSWORD=\n")
            f.write("MYSQL_DB=irequest\n")
        print("✅ .env file created")
    else:
        print("✅ .env file already exists")
    
    print("\n🔍 Current environment variables:")
    print(f"   USE_LOCAL_DB: {os.environ.get('USE_LOCAL_DB', 'Not set')}")
    print(f"   MYSQL_HOST: {os.environ.get('MYSQL_HOST', 'Not set')}")
    print(f"   MYSQL_USER: {os.environ.get('MYSQL_USER', 'Not set')}")
    print(f"   MYSQL_DB: {os.environ.get('MYSQL_DB', 'Not set')}")

if __name__ == "__main__":
    setup_environment()
    print("\n✅ Environment setup complete!")
    print("\nNext steps:")
    print("1. Make sure MySQL is running locally")
    print("2. Run: python test_db_connection.py")
    print("3. If connection test passes, run: python app.py")