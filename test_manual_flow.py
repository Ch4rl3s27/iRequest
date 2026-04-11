#!/usr/bin/env python3
"""
Test script to verify the manual clearance flow works correctly
"""
import requests
import json

def test_clearance_flow():
    """Test the manual clearance to document request flow"""
    base_url = "http://localhost:5000"
    
    try:
        # Test 1: Check if there are any approved clearances
        print("1. Checking for approved clearances...")
        response = requests.get(f"{base_url}/api/signatories/approved?office=Registrar")
        approved_data = response.json()
        
        if approved_data.get('ok') and approved_data.get('data'):
            print(f"   Found {len(approved_data['data'])} approved clearances")
            
            # Test 2: Check pending documents before move
            print("2. Checking pending documents before move...")
            response = requests.get(f"{base_url}/api/registrar/document-requests?status=pending")
            pending_before = response.json()
            print(f"   Pending documents before: {len(pending_before.get('data', []))}")
            
            # Test 3: Test the move to pending documents for first clearance
            clearance = approved_data['data'][0]
            print(f"3. Testing move to pending documents for clearance {clearance.get('request_id')}...")
            
            move_response = requests.post(f"{base_url}/api/registrar/clearance-to-document-request", 
                json={
                    "clearance_request_id": clearance.get('request_id'),
                    "student_id": clearance.get('student_id')
                })
            move_result = move_response.json()
            
            print(f"   Move result: {move_result.get('ok', False)}")
            print(f"   Message: {move_result.get('message', 'No message')}")
            
            # Test 4: Check pending documents after move
            print("4. Checking pending documents after move...")
            response = requests.get(f"{base_url}/api/registrar/document-requests?status=pending")
            pending_after = response.json()
            print(f"   Pending documents after: {len(pending_after.get('data', []))}")
            
            # Test 5: Check if the specific clearance is now in pending
            print("5. Checking if clearance is now in pending documents...")
            check_response = requests.get(f"{base_url}/api/registrar/check-pending-doc-request?student_id={clearance.get('student_id')}&clearance_request_id={clearance.get('request_id')}")
            check_result = check_response.json()
            print(f"   In pending: {check_result.get('in_pending', False)}")
            
            return True
            
        else:
            print("   No approved clearances found")
            return False
            
    except Exception as e:
        print(f"Error testing flow: {e}")
        return False

if __name__ == "__main__":
    print("Testing Manual Clearance Flow...")
    print("=" * 50)
    
    success = test_clearance_flow()
    
    print("\n" + "=" * 50)
    print(f"Test Result: {'PASS' if success else 'FAIL'}")
