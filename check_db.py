import pymysql
import json

# Connect to database (using AWS RDS credentials)
connection = pymysql.connect(
    host='irequest.ctyeeiou09cg.ap-southeast-2.rds.amazonaws.com',
    user='admin',
    password='Thesis_101',
    database='irequest',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with connection.cursor() as cursor:
        print("=== Status Synchronization Debug ===\n")
        
        # Check for Charles Edison's requests
        cursor.execute("""
            SELECT s.id, s.first_name, s.last_name, s.email
            FROM students s
            WHERE CONCAT(s.first_name, ' ', s.last_name) LIKE %s
        """, ("%Charles Edison%",))
        
        students = cursor.fetchall()
        print(f"Found {len(students)} students matching 'Charles Edison'")
        
        for student in students:
            print(f"\nStudent: {student['first_name']} {student['last_name']} (ID: {student['id']})")
            
            # Check clearance requests
            cursor.execute("""
                SELECT id, status, fulfillment_status, document_type, documents, purposes,
                       created_at, updated_at
                FROM clearance_requests 
                WHERE student_id = %s
                ORDER BY created_at DESC
            """, (student['id'],))
            
            clearance_requests = cursor.fetchall()
            print(f"\nClearance Requests ({len(clearance_requests)}):")
            for req in clearance_requests:
                print(f"  ID: {req['id']}, Status: {req['status']}, Fulfillment: {req['fulfillment_status']}")
                print(f"  Document Type: {req['document_type']}")
                print(f"  Updated: {req['updated_at']}")
            
            # Check document requests
            cursor.execute("""
                SELECT id, status, document_type, purpose, clearance_request_id,
                       created_at, updated_at
                FROM document_requests 
                WHERE student_id = %s
                ORDER BY created_at DESC
            """, (student['id'],))
            
            document_requests = cursor.fetchall()
            print(f"\nDocument Requests ({len(document_requests)}):")
            for req in document_requests:
                print(f"  ID: {req['id']}, Status: {req['status']}")
                print(f"  Document Type: {req['document_type']}")
                print(f"  Clearance Request ID: {req['clearance_request_id']}")
                print(f"  Updated: {req['updated_at']}")
            
            # Check signatories for latest clearance
            if clearance_requests:
                latest_id = clearance_requests[0]['id']
                cursor.execute("""
                    SELECT office, status, signed_by, signed_at
                    FROM clearance_signatories 
                    WHERE request_id = %s
                    ORDER BY id ASC
                """, (latest_id,))
                
                signatories = cursor.fetchall()
                print(f"\nSignatories for Clearance {latest_id} ({len(signatories)}):")
                for sig in signatories:
                    print(f"  {sig['office']}: {sig['status']} (by {sig['signed_by']})")
            
            print("=" * 80)
        
        # Fix the unlinked document request
        print("\n=== Fixing Unlinked Document Request ===\n")
        
        # Find the unlinked document request for Charles Edison
        cursor.execute("""
            SELECT dr.id, dr.status, dr.document_type, dr.purpose, dr.clearance_request_id,
                   s.first_name, s.last_name, s.id as student_id
            FROM document_requests dr
            JOIN students s ON s.id = dr.student_id
            WHERE s.first_name = 'Charles Edison' AND s.last_name = 'Andres' 
            AND dr.clearance_request_id IS NULL
        """)
        
        unlinked_docs = cursor.fetchall()
        print(f"Unlinked Document Requests: {len(unlinked_docs)}")
        
        for doc in unlinked_docs:
            print(f"  Document ID: {doc['id']}, Status: {doc['status']}")
            
            # Find the corresponding clearance request
            cursor.execute("""
                SELECT id, fulfillment_status FROM clearance_requests 
                WHERE student_id = %s 
                ORDER BY created_at DESC LIMIT 1
            """, (doc['student_id'],))
            
            clearance = cursor.fetchone()
            if clearance:
                print(f"  Found clearance request ID: {clearance['id']}, Status: {clearance['fulfillment_status']}")
                
                # Link the document request to the clearance request
                cursor.execute("""
                    UPDATE document_requests 
                    SET clearance_request_id = %s, updated_at = NOW()
                    WHERE id = %s
                """, (clearance['id'], doc['id']))
                
                print(f"  ✅ Linked document request {doc['id']} to clearance request {clearance['id']}")
                
                # Update document request status to match clearance fulfillment status
                if clearance['fulfillment_status'] == 'Processing':
                    cursor.execute("""
                        UPDATE document_requests 
                        SET status = 'Processing', updated_at = NOW()
                        WHERE id = %s
                    """, (doc['id'],))
                    print(f"  ✅ Updated document request status to 'Processing'")
                
                # Commit the changes
                connection.commit()
                print(f"  ✅ Changes committed to database")
            else:
                print(f"  ❌ No clearance request found for student {doc['student_id']}")
        
        # Check all processing requests
        print("\n=== All Processing Requests ===\n")
        
        cursor.execute("""
            SELECT dr.id, dr.status, dr.document_type, dr.purpose, dr.clearance_request_id,
                   s.first_name, s.last_name, dr.created_at, dr.updated_at
            FROM document_requests dr
            JOIN students s ON s.id = dr.student_id
            WHERE dr.status = 'Processing'
            ORDER BY dr.updated_at DESC
        """)
        
        processing_docs = cursor.fetchall()
        print(f"Document Requests in Processing: {len(processing_docs)}")
        for doc in processing_docs:
            print(f"  Student: {doc['first_name']} {doc['last_name']}")
            print(f"  Document ID: {doc['id']}")
            print(f"  Status: {doc['status']}")
            print(f"  Document Type: {doc['document_type']}")
            print(f"  Clearance Request ID: {doc['clearance_request_id']}")
            print(f"  Updated: {doc['updated_at']}")
            print()
            
finally:
    connection.close()
