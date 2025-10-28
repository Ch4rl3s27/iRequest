#!/usr/bin/env python3
"""
Test script to verify the clearance transfer fix
"""
import requests
import json

def test_fix_missing_transfers():
    """Test the fix missing transfers endpoint"""
    try:
        # Test the fix endpoint
        response = requests.post('http://localhost:5000/api/registrar/fix-missing-transfers')
        result = response.json()
        
        print("Fix Missing Transfers Result:")
        print(f"Status: {result.get('ok', False)}")
        print(f"Message: {result.get('message', 'No message')}")
        print(f"Fixed Count: {result.get('fixed_count', 0)}")
        print(f"Total Found: {result.get('total_found', 0)}")
        
        return result.get('ok', False)
        
    except Exception as e:
        print(f"Error testing fix: {e}")
        return False

def test_pending_documents():
    """Test the pending documents endpoint"""
    try:
        # Test the pending documents endpoint
        response = requests.get('http://localhost:5000/api/registrar/document-requests?status=pending')
        result = response.json()
        
        print("\nPending Documents Result:")
        print(f"Status: {result.get('ok', False)}")
        print(f"Count: {len(result.get('data', []))}")
        
        if result.get('data'):
            print("Documents found:")
            for doc in result.get('data', []):
                print(f"  - {doc.get('student_name', 'Unknown')}: {doc.get('document', 'Unknown')}")
        
        return result.get('ok', False)
        
    except Exception as e:
        print(f"Error testing pending documents: {e}")
        return False

if __name__ == "__main__":
    print("Testing Clearance Transfer Fix...")
    print("=" * 50)
    
    # Test the fix
    fix_success = test_fix_missing_transfers()
    
    # Test pending documents
    pending_success = test_pending_documents()
    
    print("\n" + "=" * 50)
    print(f"Fix Test: {'PASS' if fix_success else 'FAIL'}")
    print(f"Pending Documents Test: {'PASS' if pending_success else 'FAIL'}")
