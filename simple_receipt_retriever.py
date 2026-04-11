#!/usr/bin/env python3
"""
Simple script to retrieve receipt data using the existing app database connection
"""

import sys
import os
import base64
from datetime import datetime

# Add the current directory to Python path to import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_receipt_from_database(request_id):
    """
    Retrieve receipt data from the database using the existing app connection
    """
    try:
        # Import the app and database connection
        from app import create_app
        from app.models import db, ClearanceRequest, Student
        
        # Create app instance
        app = create_app()
        
        with app.app_context():
            # Query to get receipt data using SQLAlchemy
            query = db.session.query(
                ClearanceRequest.id,
                ClearanceRequest.student_id,
                ClearanceRequest.payment_receipt,
                ClearanceRequest.payment_method,
                ClearanceRequest.payment_amount,
                ClearanceRequest.reference_number,
                ClearanceRequest.created_at,
                Student.first_name,
                Student.last_name,
                Student.student_id.label('student_no'),
                Student.email
            ).join(Student, Student.id == ClearanceRequest.student_id).filter(
                ClearanceRequest.id == request_id
            )
            
            print(f"🔍 Fetching receipt for request ID: {request_id}")
            result = query.first()
            
            if result:
                print(f"✅ Found clearance request:")
                print(f"   📄 ID: {result.id}")
                print(f"   👤 Student: {result.first_name} {result.last_name} ({result.student_no})")
                print(f"   📧 Email: {result.email}")
                print(f"   💰 Payment Method: {result.payment_method or 'Not specified'}")
                print(f"   💵 Payment Amount: {result.payment_amount or 'Not specified'}")
                print(f"   🔢 Reference Number: {result.reference_number or 'Not provided'}")
                print(f"   📅 Created: {result.created_at}")
                
                if result.payment_receipt:
                    print(f"   📸 Receipt Image: Available (Base64 length: {len(result.payment_receipt)})")
                    
                    # Ask if user wants to save the image
                    save_choice = input("\n💾 Do you want to save the receipt image? (y/n): ").lower()
                    if save_choice == 'y':
                        save_receipt_image(result.payment_receipt, result.id, result.student_no)
                else:
                    print(f"   📸 Receipt Image: Not available")
                
                return result
            else:
                print(f"❌ No clearance request found with ID: {request_id}")
                return None
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

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

def list_all_receipts():
    """List all clearance requests with receipt images"""
    try:
        from app import create_app
        from app.models import db, ClearanceRequest, Student
        
        app = create_app()
        
        with app.app_context():
            # Query to get all requests with receipts using SQLAlchemy
            query = db.session.query(
                ClearanceRequest.id,
                ClearanceRequest.student_id,
                ClearanceRequest.payment_receipt,
                ClearanceRequest.payment_method,
                ClearanceRequest.payment_amount,
                ClearanceRequest.reference_number,
                ClearanceRequest.created_at,
                Student.first_name,
                Student.last_name,
                Student.student_id.label('student_no'),
                Student.email
            ).join(Student, Student.id == ClearanceRequest.student_id).filter(
                ClearanceRequest.payment_receipt.isnot(None)
            ).order_by(ClearanceRequest.created_at.desc())
            
            results = query.all()
            
            print(f"📊 Found {len(results)} clearance requests with receipt images:")
            print("-" * 80)
            
            for i, result in enumerate(results, 1):
                receipt_status = "✅ Has receipt" if result.payment_receipt else "❌ No receipt"
                print(f"{i:2d}. ID: {result.id:3d} | {result.first_name} {result.last_name} | "
                      f"Student: {result.student_no} | {receipt_status}")
            
            return results
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🔍 iRequest Receipt Retriever")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        # Command line argument provided
        try:
            request_id = int(sys.argv[1])
            get_receipt_from_database(request_id)
        except ValueError:
            print("❌ Please provide a valid request ID number")
    else:
        # Interactive mode
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
                    get_receipt_from_database(request_id)
                except ValueError:
                    print("❌ Please enter a valid request ID number")
            
            elif choice == '2':
                list_all_receipts()
            
            elif choice == '3':
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")
