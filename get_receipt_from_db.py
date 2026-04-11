#!/usr/bin/env python3
"""
Script to retrieve receipt data from the iRequest database
"""

import pymysql
import json
import base64
import os
from datetime import datetime

def connect_to_database():
    """Connect to the MySQL database"""
    try:
        # Database connection parameters - adjust these based on your config
        connection = pymysql.connect(
            host='localhost',
            user='root',  # Update with your MySQL username
            password='',  # Update with your MySQL password
            database='irequest',  # Update with your database name
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("✅ Successfully connected to database")
        return connection
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def get_receipt_data(connection, request_id=None):
    """Retrieve receipt data from the database"""
    try:
        cursor = connection.cursor()
        
        if request_id:
            # Get specific request
            query = """
                SELECT cr.id, cr.student_id, cr.payment_receipt, cr.payment_method, 
                       cr.payment_amount, cr.reference_number, cr.created_at,
                       s.first_name, s.last_name, s.student_no, s.email
                FROM clearance_requests cr
                JOIN students s ON s.id = cr.student_id
                WHERE cr.id = %s
            """
            cursor.execute(query, (request_id,))
            result = cursor.fetchone()
            
            if result:
                print(f"📄 Found clearance request ID: {result['id']}")
                print(f"👤 Student: {result['first_name']} {result['last_name']} ({result['student_no']})")
                print(f"📧 Email: {result['email']}")
                print(f"💰 Payment Method: {result['payment_method'] or 'Not specified'}")
                print(f"💵 Payment Amount: {result['payment_amount'] or 'Not specified'}")
                print(f"🔢 Reference Number: {result['reference_number'] or 'Not provided'}")
                print(f"📅 Created: {result['created_at']}")
                
                if result['payment_receipt']:
                    print(f"📸 Receipt Image: Available (Base64 length: {len(result['payment_receipt'])})")
                    
                    # Ask if user wants to save the image
                    save_image = input("\n💾 Do you want to save the receipt image to a file? (y/n): ").lower()
                    if save_image == 'y':
                        save_receipt_image(result['payment_receipt'], result['id'], result['student_no'])
                else:
                    print("📸 Receipt Image: Not available")
                
                return result
            else:
                print(f"❌ No clearance request found with ID: {request_id}")
                return None
        else:
            # Get all requests with receipts
            query = """
                SELECT cr.id, cr.student_id, cr.payment_receipt, cr.payment_method, 
                       cr.payment_amount, cr.reference_number, cr.created_at,
                       s.first_name, s.last_name, s.student_no, s.email
                FROM clearance_requests cr
                JOIN students s ON s.id = cr.student_id
                WHERE cr.payment_receipt IS NOT NULL
                ORDER BY cr.created_at DESC
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            print(f"📊 Found {len(results)} clearance requests with receipt images:")
            print("-" * 80)
            
            for i, result in enumerate(results, 1):
                receipt_status = "✅ Has receipt" if result['payment_receipt'] else "❌ No receipt"
                print(f"{i:2d}. ID: {result['id']:3d} | {result['first_name']} {result['last_name']} | "
                      f"Student: {result['student_no']} | {receipt_status}")
            
            return results
            
    except Exception as e:
        print(f"❌ Error retrieving receipt data: {e}")
        return None
    finally:
        cursor.close()

def save_receipt_image(base64_data, request_id, student_no):
    """Save receipt image to file"""
    try:
        # Decode base64 data
        image_data = base64.b64decode(base64_data)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"receipt_request_{request_id}_student_{student_no}_{timestamp}.jpg"
        
        # Save to file
        with open(filename, 'wb') as f:
            f.write(image_data)
        
        print(f"💾 Receipt image saved as: {filename}")
        print(f"📁 File size: {len(image_data)} bytes")
        
    except Exception as e:
        print(f"❌ Error saving receipt image: {e}")

def main():
    """Main function"""
    print("🔍 iRequest Receipt Database Retriever")
    print("=" * 50)
    
    # Connect to database
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        while True:
            print("\n📋 Options:")
            print("1. Get specific clearance request by ID")
            print("2. List all requests with receipts")
            print("3. Exit")
            
            choice = input("\n👉 Enter your choice (1-3): ").strip()
            
            if choice == '1':
                request_id = input("🔢 Enter clearance request ID: ").strip()
                try:
                    request_id = int(request_id)
                    get_receipt_data(connection, request_id)
                except ValueError:
                    print("❌ Please enter a valid request ID number")
            
            elif choice == '2':
                get_receipt_data(connection)
            
            elif choice == '3':
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")
    
    finally:
        connection.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    main()
