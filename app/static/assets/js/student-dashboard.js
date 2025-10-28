// Auto-refresh requests every 30 seconds
let refreshInterval;

async function loadRequests() {
  try {
    const res = await fetch('/api/student/requests');
    const data = await res.json();
    
    if (!data.ok) throw new Error(data.message || 'Failed to load requests');
    
    const tbody = document.getElementById('requestsList');
    if (!tbody) return;
    
    // Clear existing rows
    tbody.innerHTML = '';
    
    if (data.requests?.length) {
      data.requests.forEach(req => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>
            <div class="d-flex align-items-center">
              <div class="flex-shrink-0">
                <i class="fas fa-file-alt text-primary"></i>
              </div>
              <div class="ms-3">
                <p class="fw-semibold mb-0">Request #${req.id}</p>
                <small class="text-muted">${new Date(req.date_requested).toLocaleDateString()}</small>
              </div>
            </div>
          </td>
          <td>
            <span class="badge ${getStatusBadgeClass(req.status)}">
              ${req.status}
            </span>
          </td>
          <td>${req.updated_at ? new Date(req.updated_at).toLocaleDateString() : '—'}</td>
          <td>
            <button class="btn btn-sm btn-outline-primary" onclick="viewDetails(${req.id})">
              <i class="fas fa-eye me-1"></i> View
            </button>
          </td>`;
        tbody.appendChild(tr);
      });
    } else {
      tbody.innerHTML = `
        <tr>
          <td colspan="4" class="text-center py-4 text-muted">
            <i class="fas fa-inbox fa-2x mb-2 d-block"></i>
            No requests found
          </td>
        </tr>`;
    }
    
    // Update request counts
    updateRequestCounts(data.requests || []);
    
  } catch(err) {
    console.error('Error loading requests:', err);
    const tbody = document.getElementById('requestsList');
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="4" class="text-center py-4 text-danger">
            <i class="fas fa-exclamation-circle fa-2x mb-2 d-block"></i>
            Failed to load requests. Please try again.
          </td>
        </tr>`;
    }
  }
}

function getStatusBadgeClass(status) {
  switch(status?.toLowerCase()) {
    case 'pending': return 'bg-warning';
    case 'approved': return 'bg-success';
    case 'rejected': return 'bg-danger';
    case 'processing': return 'bg-primary';
    default: return 'bg-secondary';
  }
}

function getEffectiveStatus(req){
  const raw = (req.status || '').toString().trim().toLowerCase(); // registrar fulfillment_status when available
  const signatories = Array.isArray(req.signatories) ? req.signatories : [];
  const requestType = req.request_type || 'clearance'; // Default to clearance for backward compatibility
  
  // Handle consolidated requests (clearance + document combined)
  if (requestType === 'consolidated') {
    // For consolidated requests, use the document status as the primary status
    if (raw === 'completed') return 'released';
    if (raw === 'processing') return 'processing';
    if (raw === 'rejected') return 'rejected';
    return 'pending';
  }
  
  // Handle document requests (post-auto-transfer)
  if (requestType === 'document') {
    // For document requests, show completed as a separate stage visible to student
    if (raw === 'completed') return 'completed';
    if (raw === 'released') return 'released';
    if (raw === 'processing') return 'processing';
    if (raw === 'rejected') return 'rejected';
    if (raw === 'unclaimed') return 'released';
    return 'pending';
  }
  
  // Handle clearance requests (pre-auto-transfer)
  // Handle standalone document requests (no signatories) - legacy support
  if (signatories.length === 0) {
    // For legacy standalone document requests
    if (raw === 'completed') return 'completed';
    if (raw === 'released') return 'released';
    if (raw === 'processing') return 'processing';
    if (raw === 'rejected') return 'rejected';
    return 'pending';
  }
  
  // Handle clearance requests (with signatories)
  const hasAnyRejected = signatories.some(function(s){ return (s.status || '').toString().toLowerCase() === 'rejected'; });
  const allApproved = signatories.length > 0 && signatories.every(function(s){ return (s.status || '').toString().toLowerCase() === 'approved'; });

  // If any office rejected, whole request is Rejected
  if (hasAnyRejected) return 'rejected';

  // If not all signatories have approved yet, remain Pending
  if (!allApproved) return 'pending';

  // All signatories approved → rely on Registrar fulfillment status
  // Show the actual registrar status for better synchronization
  if (raw === 'processing') return 'processing';
  if (raw === 'rejected') return 'rejected';
  if (raw === 'completed') return 'completed';
  if (raw === 'released') return 'released';

  // Default when Registrar has not started (e.g., fulfillment_status Pending or unknown)
  return 'pending';
}

function updateRequestCounts(requests) {
  const counts = {
    pending: 0,
    processing: 0,
    completed: 0
  };
  
  // Use getEffectiveStatus function to properly categorize requests
  requests.forEach(r => {
    const effectiveStatus = getEffectiveStatus(r);
    if (effectiveStatus === 'pending') counts.pending++;
    else if (effectiveStatus === 'processing') counts.processing++;
    else if (effectiveStatus === 'released') counts.completed++;
  });
  
  // Update count displays
  Object.entries(counts).forEach(([type, count]) => {
    const countEl = document.querySelector(`.${type} .count`);
    if (countEl) countEl.textContent = count;
  });
}

// Load and display existing requests
async function loadExistingRequests() {
  try {
    const response = await fetch('/api/student/existing-requests');
    const data = await response.json();
    
    if (data.ok && data.requests && data.requests.length > 0) {
      const existingRequestsContainer = document.getElementById('existingRequestsContainer');
      if (existingRequestsContainer) {
        const requestsHtml = data.requests.map(req => {
          const statusClass = req.status === 'Approved' ? 'status-approved' : 
                            req.status === 'Rejected' ? 'status-rejected' : 'status-pending';
          const statusText = req.status === 'Pending' ? 'Pending' : 
                           req.status === 'Approved' ? 'Approved' : 'Rejected';
          const createdDate = new Date(req.created_at).toLocaleDateString();
          
          return `
            <div class="existing-request-item">
              <div class="request-info">
                <span class="request-id">Request #${req.id}</span>
                <span class="request-status ${statusClass}">${statusText}</span>
                <span class="request-date">${createdDate}</span>
              </div>
              <div class="request-details">
                <strong>Documents:</strong> ${req.documents.join(', ')}<br>
                <strong>Purpose:</strong> ${req.purposes.join(', ')}
              </div>
            </div>
          `;
        }).join('');
        
        existingRequestsContainer.innerHTML = `
          <div class="existing-requests-header">
            <h4>Your Recent Requests (Last 30 Days)</h4>
            <p>Please check if you already have a similar request before submitting a new one.</p>
          </div>
          <div class="existing-requests-list">
            ${requestsHtml}
          </div>
        `;
        
        existingRequestsContainer.style.display = 'block';
      }
    }
  } catch (error) {
    console.error('Error loading existing requests:', error);
  }
}

// Handle request submission
async function submitRequest() {
  const submitButton = document.querySelector('.submit-btn');
  
  try {
    // Show loading state
    if (submitButton && window.buttonLoadingManager) {
      window.buttonLoadingManager.showLoading(submitButton, 'Checking for duplicates...', true);
    }
    
    // Collect selected choices from DOM if present
    const selectedDocs = Array.from(document.querySelectorAll('input[name="requestedDocument"]:checked')).map(cb => cb.value);
    const selectedPurposes = Array.from(document.querySelectorAll('input[name="clearancePurpose"]:checked')).map(cb => {
      if (cb.value === 'Other') {
        const otherInput = cb.nextElementSibling;
        return otherInput && otherInput.value ? otherInput.value : null;
      }
      return cb.value;
    }).filter(Boolean);
    const reasonInput = document.querySelector('#clearanceReason');
    const reason = reasonInput ? (reasonInput.value || '') : '';

    // First check for duplicates
    const duplicateCheck = await fetch('/api/clearance/check-duplicate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        documents: selectedDocs, 
        purposes: selectedPurposes, 
        reason,
        document_type: 'Registrar Documents'
      })
    });
    
    const duplicateData = await duplicateCheck.json();
    
    if (duplicateData.is_duplicate) {
      // Show duplicate warning with option to proceed
      const result = await Swal.fire({
        title: 'Duplicate Request Detected',
        html: `
          <div style="text-align: left;">
            <p><strong>${duplicateData.message}</strong></p>
            <p>Are you sure you want to submit a new request anyway?</p>
            <p style="color: #666; font-size: 0.9em;">
              <em>Note: This will create a separate request that will be processed independently.</em>
            </p>
          </div>
        `,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Yes, Submit Anyway',
        cancelButtonText: 'Cancel',
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6'
      });
      
      if (!result.isConfirmed) {
        if (submitButton && window.buttonLoadingManager) {
          window.buttonLoadingManager.hideLoading(submitButton);
        }
        return;
      }
    }

    // Update loading text
    if (submitButton && window.buttonLoadingManager) {
      window.buttonLoadingManager.showLoading(submitButton, 'Submitting Request...', true);
    }

    // Submit the request
    const res = await fetch('/api/clearance/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ documents: selectedDocs, purposes: selectedPurposes, reason })
    });
    const data = await res.json();
    
    if (!data.ok) throw new Error(data.message || 'Failed to submit request');
    
    // Show success message
    Swal.fire({
      title: 'Request Submitted',
      text: 'Your clearance request has been submitted successfully.',
      icon: 'success',
      confirmButtonText: 'OK'
    });
    
    // Refresh the requests list
    loadRequests();
    
  } catch(err) {
    console.error('Error submitting request:', err);
    Swal.fire({
      title: 'Error',
      text: err.message || 'Failed to submit request. Please try again.',
      icon: 'error',
      confirmButtonText: 'OK'
    });
  } finally {
    // Hide loading state
    if (submitButton && window.buttonLoadingManager) {
      window.buttonLoadingManager.hideLoading(submitButton);
    }
  }
}

// View request details
async function viewDetails(requestId) {
  const viewButton = event?.target?.closest('button');
  
  try {
    // Show loading state
    if (viewButton && window.buttonLoadingManager) {
      window.buttonLoadingManager.showLoading(viewButton, 'Loading Details...', true);
    }
    
    const res = await fetch(`/api/clearance/request/${requestId}`);
    const data = await res.json();
    
    if (!data.ok) throw new Error(data.message || 'Failed to load request details');
    
    const req = data.request;
    const signatories = data.signatories || [];
    
    // Format request date
    const requestDate = req.date_requested ? new Date(req.date_requested).toLocaleString() : '—';
    
    // Get payment information
    const paymentMethod = req.payment_method || 'Cash';
    const paymentStatus = req.payment_status || 'Pending';
    const paymentStatusClass = paymentStatus.toLowerCase() === 'paid' ? 'payment-paid' : 'payment-pending';
    
    // Create signatory rows with better styling
    const signatoryList = signatories.map(s => {
      const statusLower = (s.status || '').toLowerCase();
      const statusIcon = statusLower === 'approved' ? 'fa-check-circle' : 
                        statusLower === 'pending' ? 'fa-clock' : 'fa-times-circle';
      const statusClass = statusLower === 'approved' ? 'status-approved' : 
                         statusLower === 'rejected' ? 'status-rejected' : 'status-pending';
      
      return `
        <tr class="office-row">
          <td class="office-name">
            <div class="office-info">
              <i class="fas fa-building office-icon"></i>
              <span>${s.office}</span>
            </div>
          </td>
          <td class="status-cell">
            <span class="status-badge ${statusClass}">
              <i class="fas ${statusIcon}"></i>
              ${s.status}
            </span>
          </td>
          <td class="signed-by">${s.signed_by || '—'}</td>
          <td class="date-cell">${s.signed_at ? new Date(s.signed_at).toLocaleDateString() : '—'}</td>
          <td class="reason-cell">${s.rejection_reason || '—'}</td>
        </tr>
      `;
    }).join('');
    
    Swal.fire({
      title: 'Office Clearance Status',
      html: `
        <div class="clearance-modal">
          <!-- Request Information Header -->
          <div class="request-header">
            <div class="request-info">
              <div class="info-item">
                <i class="fas fa-calendar-alt"></i>
                <span class="info-label">Date Requested:</span>
                <span class="info-value">${requestDate}</span>
              </div>
              <div class="info-item">
                <i class="fas fa-credit-card"></i>
                <span class="info-label">Payment Method:</span>
                <span class="info-value">${paymentMethod} (₱50)</span>
              </div>
              <div class="info-item">
                <i class="fas fa-check-circle"></i>
                <span class="info-label">Payment Status:</span>
                <span class="info-value ${paymentStatusClass}">${paymentStatus}</span>
              </div>
            </div>
          </div>
          
          <!-- Office Clearance Status Table -->
          <div class="clearance-table-container">
            <div class="table-header">
              <h4><i class="fas fa-clipboard-check"></i> Office Clearance Status</h4>
            </div>
            <div class="table-wrapper">
              <table class="clearance-table">
                <thead>
                  <tr>
                    <th class="office-col">Office</th>
                    <th class="status-col">Status</th>
                    <th class="signed-col">Signed By</th>
                    <th class="date-col">Date</th>
                    <th class="reason-col">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  ${signatoryList}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      `,
      width: '900px',
      showConfirmButton: true,
      showDenyButton: true,
      confirmButtonText: '<i class="fas fa-times"></i> Close',
      denyButtonText: '<i class="fas fa-print"></i> Print',
      confirmButtonColor: '#6c757d',
      denyButtonColor: '#dc3545',
      customClass: {
        popup: 'clearance-modal-popup',
        htmlContainer: 'clearance-modal-content'
      }
    }).then((result) => {
      if (result.isDenied) {
        // Print functionality
        window.print();
      }
    });
    
  } catch(err) {
    console.error('Error loading request details:', err);
    Swal.fire({
      title: 'Error',
      text: 'Failed to load request details. Please try again.',
      icon: 'error',
      confirmButtonText: 'OK'
    });
  } finally {
    // Hide loading state
    if (viewButton && window.buttonLoadingManager) {
      window.buttonLoadingManager.hideLoading(viewButton);
    }
  }
}

// Enhanced loading with full-screen overlay
async function loadRequestsWithFullScreenLoading() {
  try {
    // Show full-screen loading
    if (window.showFullScreenLoading) {
      window.showFullScreenLoading('Loading Dashboard...');
    }
    
    // Load the data
    await loadRequests();
    
  } catch (error) {
    console.error('Error loading requests:', error);
  } finally {
    // Hide full-screen loading
    if (window.hideFullScreenLoading) {
      window.hideFullScreenLoading();
    }
  }
}

// Setup auto-refresh when page loads
document.addEventListener('DOMContentLoaded', () => {
  loadRequestsWithFullScreenLoading(); // Initial load with full-screen loading
  loadExistingRequests(); // Load existing requests for duplicate prevention
  refreshInterval = setInterval(loadRequestsWithFullScreenLoading, 30000); // Refresh every 30 seconds
});

// Cleanup interval when page unloads
window.addEventListener('unload', () => {
  if (refreshInterval) clearInterval(refreshInterval);
});