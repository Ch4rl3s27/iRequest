/**
 * Receipt Modal Utility
 * Handles displaying receipt images in a responsive modal
 */

class ReceiptModal {
  constructor() {
    console.log('🔍 Receipt Modal: Constructor called');
    this.modal = null;
    this.isOpen = false;
    this.currentImage = null;
    this.initialized = false;
    this.init();
    console.log('🔍 Receipt Modal: Constructor completed');
  }

  init() {
    console.log('🔍 Receipt Modal: init() called');
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      console.log('🔍 Receipt Modal: DOM still loading, waiting for DOMContentLoaded');
      document.addEventListener('DOMContentLoaded', () => this.initializeModal());
    } else {
      console.log('🔍 Receipt Modal: DOM ready, initializing modal immediately');
      this.initializeModal();
    }
  }

  initializeModal() {
    console.log('🔍 Receipt Modal: initializeModal() called');
    if (this.initialized) {
      console.log('🔍 Receipt Modal: Already initialized, returning');
      return;
    }
    
    console.log('🔍 Receipt Modal: Creating modal HTML...');
    // Create modal HTML if it doesn't exist
    if (!document.getElementById('receipt-modal')) {
      this.createModal();
    }
    this.modal = document.getElementById('receipt-modal');
    this.bindEvents();
    this.initialized = true;
  }

  createModal() {
    // Ensure document.body exists
    if (!document.body) {
      console.error('Document body not available for receipt modal');
      return;
    }
    
    const modalHTML = `
      <div id="receipt-modal" class="receipt-modal">
        <div class="receipt-modal-content">
          <div class="receipt-modal-header">
            <h3 class="receipt-modal-title">
              <span class="receipt-modal-title-icon"><i class="fas fa-file-invoice-dollar"></i></span>
              Payment Receipt
            </h3>
            <button class="receipt-modal-close" type="button" aria-label="Close">
              <i class="fas fa-times"></i>
            </button>
          </div>
          <div class="receipt-modal-body">
            <div class="receipt-loading" id="receipt-loading">
              <div class="receipt-loading-spinner"></div>
              <div class="receipt-loading-text">Loading receipt...</div>
            </div>
            <div class="receipt-error" id="receipt-error" style="display: none;">
              <div class="receipt-error-icon">
                <i class="fas fa-exclamation-triangle"></i>
              </div>
              <div class="receipt-error-text">Failed to load receipt</div>
              <div class="receipt-error-subtext" id="receipt-error-message">Please try again later</div>
            </div>
            <div class="receipt-no-image" id="receipt-no-image" style="display: none;">
              <div class="receipt-no-image-icon">
                <i class="fas fa-receipt"></i>
              </div>
              <div class="receipt-no-image-text">No Receipt Uploaded</div>
              <div class="receipt-no-image-subtext">This request doesn't have a payment receipt</div>
            </div>
            <div class="receipt-image-container" id="receipt-image-container" style="display: none;">
              <img class="receipt-image" id="receipt-image" alt="Payment Receipt" />
            </div>
          </div>
          <div class="receipt-modal-actions" id="receipt-modal-actions" style="display: none;">
            <button class="receipt-btn receipt-btn-secondary" id="receipt-zoom-btn" type="button">
              <i class="fas fa-search-plus"></i> Zoom
            </button>
            <button class="receipt-btn receipt-btn-secondary" id="receipt-download-btn" type="button">
              <i class="fas fa-download"></i> Download
            </button>
            <button class="receipt-btn receipt-btn-primary" id="receipt-close-btn" type="button">
              Close
            </button>
          </div>
        </div>
      </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
  }

  bindEvents() {
    // Close modal events
    const closeBtn = this.modal.querySelector('.receipt-modal-close');
    const closeActionBtn = this.modal.querySelector('#receipt-close-btn');
    const zoomBtn = this.modal.querySelector('#receipt-zoom-btn');
    const downloadBtn = this.modal.querySelector('#receipt-download-btn');
    const image = this.modal.querySelector('#receipt-image');

    closeBtn.addEventListener('click', () => this.close());
    closeActionBtn.addEventListener('click', () => this.close());
    
    // Close on backdrop click
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.close();
      }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen) {
        this.close();
      }
    });

    // Zoom functionality
    zoomBtn.addEventListener('click', () => this.toggleZoom());
    image.addEventListener('click', () => this.toggleZoom());

    // Download functionality
    downloadBtn.addEventListener('click', () => this.downloadImage());
  }

  async show(requestId) {
    console.log('🔍 Receipt Modal: show() called with requestId:', requestId);
    
    // Validate requestId
    if (!requestId || requestId === 'undefined' || requestId === 'null') {
      console.error('🔍 Receipt Modal: Invalid requestId:', requestId);
      this.showError('Invalid request ID provided');
      return;
    }
    
    // Ensure modal is initialized
    if (!this.initialized) {
      console.log('🔍 Receipt Modal: Initializing modal...');
      this.initializeModal();
    }
    
    if (!this.modal) {
      console.error('🔍 Receipt Modal: Modal not available after initialization');
      this.showError('Receipt modal not available');
      return;
    }

    if (this.isOpen) {
      this.close();
    }

    this.isOpen = true;
    this.modal.classList.add('show');
    this.showLoading();

    try {
      console.log('🔍 Receipt Modal: Fetching receipt for requestId:', requestId);
      const response = await fetch(`/api/receipt/${requestId}`);
      console.log('🔍 Receipt Modal: Response status:', response.status);
      
      if (!response.ok) {
        console.error('🔍 Receipt Modal: HTTP error:', response.status, response.statusText);
        this.showError(`Server error: ${response.status} ${response.statusText}`);
        return;
      }
      
      const data = await response.json();
      console.log('🔍 Receipt Modal: API response:', data);

      if (data && data.ok) {
        // Store student info for display
        this.studentInfo = data.student_info;
        console.log('🔍 Receipt Modal: Student info:', this.studentInfo);
        
        if (data.image_url) {
          // Receipt image available from S3
          console.log('🔍 Receipt Modal: Loading image from S3 URL');
          this.loadImageFromUrl(data.image_url);
        } else if (data.image_data) {
          // Receipt image available from database
          console.log('🔍 Receipt Modal: Loading image from database');
          this.loadImageFromData(data.image_data);
        } else if (data.no_receipt && data.payment_info) {
          // No receipt image, but payment info available
          console.log('🔍 Receipt Modal: Showing payment info only');
          this.showPaymentInfo(data.payment_info, data.message);
        } else {
          // No receipt or payment info
          console.log('🔍 Receipt Modal: No receipt or payment info');
          this.showNoImage();
        }
      } else {
        console.error('🔍 Receipt Modal: API returned error:', data);
        this.showError(data?.message || 'Failed to load receipt');
      }
    } catch (error) {
      console.error('🔍 Receipt Modal: Network error:', error);
      this.showError('Network error. Please check your connection and try again.');
    }
  }

  loadImageFromUrl(imageUrl) {
    console.log('🔍 Receipt Modal: Loading image from URL');
    const img = this.modal.querySelector('#receipt-image');
    
    if (!imageUrl) {
      console.error('🔍 Receipt Modal: No image URL provided');
      this.showError('No image URL available');
      return;
    }
    
    // Set the image source to the S3 URL
    img.src = imageUrl;
    
    // Add error handling for failed image loads
    img.onerror = () => {
      console.error('🔍 Receipt Modal: Failed to load image from URL:', imageUrl);
      this.showError('Failed to load receipt image. The image may have expired or is no longer available.');
    };
    
    img.onload = () => {
      console.log('🔍 Receipt Modal: Image loaded successfully from URL');
      this.showImage();
    };
  }

  loadImageFromData(base64Data) {
    console.log('🔍 Receipt Modal: Loading image from database data');
    const img = this.modal.querySelector('#receipt-image');
    
    if (!base64Data) {
      console.error('🔍 Receipt Modal: No base64 data provided');
      this.showError('No image data available');
      return;
    }
    
    // Try different image formats since students might upload different types
    if (base64Data.startsWith('/9j/') || base64Data.startsWith('iVBOR')) {
      // It's already base64 encoded, use it directly
      img.src = `data:image/jpeg;base64,${base64Data}`;
    } else {
      // Assume it's base64 data and add the data URL prefix
      img.src = `data:image/jpeg;base64,${base64Data}`;
    }
    
    console.log('🔍 Receipt Modal: Image src set, showing image');
    this.showImage();
  }

  showLoading() {
    this.hideAllStates();
    this.modal.querySelector('#receipt-loading').style.display = 'flex';
    this.modal.querySelector('#receipt-modal-actions').style.display = 'none';
  }

  showImage() {
    this.hideAllStates();
    this.modal.querySelector('#receipt-image-container').style.display = 'block';
    this.modal.querySelector('#receipt-modal-actions').style.display = 'flex';
    this.currentImage = this.modal.querySelector('#receipt-image');
    
    // Display student information if available
    this.displayStudentInfo();
  }

  showError(message) {
    this.hideAllStates();
    this.modal.querySelector('#receipt-error').style.display = 'flex';
    this.modal.querySelector('#receipt-error-message').textContent = message;
    this.modal.querySelector('#receipt-modal-actions').style.display = 'flex';
  }

  showNoImage() {
    this.hideAllStates();
    this.modal.querySelector('#receipt-no-image').style.display = 'flex';
    this.modal.querySelector('#receipt-modal-actions').style.display = 'flex';
  }

  showPaymentInfo(paymentInfo, message) {
    this.hideAllStates();
    
    // Create payment info display if it doesn't exist
    let paymentInfoContainer = this.modal.querySelector('#receipt-payment-info');
    if (!paymentInfoContainer) {
      paymentInfoContainer = document.createElement('div');
      paymentInfoContainer.id = 'receipt-payment-info';
      paymentInfoContainer.style.cssText = `
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem 1.25rem;
        text-align: center;
        background: #ffffff;
        border-radius: 12px;
        margin: 0;
        border: 1px solid #e2e8f0;
      `;
      
      const modalBody = this.modal.querySelector('.receipt-modal-body');
      modalBody.appendChild(paymentInfoContainer);
    }
    
    paymentInfoContainer.innerHTML = `
      <div style="margin-bottom: 1.25rem;">
        <i class="fas fa-receipt" style="font-size: 2.25rem; color: #94a3b8; margin-bottom: 0.75rem;"></i>
        <h4 style="color: #0f172a; font-size: 1rem; font-weight: 600; margin-bottom: 0.25rem;">Payment Information</h4>
        <p style="color: #64748b; font-size: 0.875rem;">${message}</p>
      </div>
      
      <div style="background: #f8fafc; border-radius: 10px; padding: 1.25rem; width: 100%; max-width: 400px; border: 1px solid #e2e8f0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid #e2e8f0;">
          <span style="font-weight: 600; color: #475569;">Payment Method:</span>
          <span style="color: #64748b;">${paymentInfo.method}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid #e2e8f0;">
          <span style="font-weight: 600; color: #475569;">Amount:</span>
          <span style="color: #059669; font-weight: 600;">₱${paymentInfo.amount}</span>
        </div>
        <div style="display: flex; justify-content: space-between;">
          <span style="font-weight: 600; color: #475569;">Reference Number:</span>
          <span style="color: #64748b; font-family: ui-monospace, monospace;">${paymentInfo.reference_number}</span>
        </div>
      </div>
      
      <div style="margin-top: 1.25rem; padding: 0.75rem 1rem; background: #fffbeb; border-radius: 8px; border: 1px solid #fde68a;">
        <p style="margin: 0; color: #92400e; font-size: 0.8125rem;">
          <i class="fas fa-info-circle" style="margin-right: 0.375rem;"></i>
          No receipt image was uploaded for this request. Contact the registrar if you need to upload a receipt.
        </p>
      </div>
    `;
    
    paymentInfoContainer.style.display = 'flex';
    this.modal.querySelector('#receipt-modal-actions').style.display = 'flex';
    
    // Display student information if available
    this.displayStudentInfo();
  }

  displayStudentInfo() {
    if (!this.studentInfo) return;
    
    // Create or update student info display
    let studentInfoContainer = this.modal.querySelector('#receipt-student-info');
    if (!studentInfoContainer) {
      studentInfoContainer = document.createElement('div');
      studentInfoContainer.id = 'receipt-student-info';
      studentInfoContainer.style.cssText = `
        background: #ffffff;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin: 0 0 1rem 0;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #2563eb;
      `;
      
      // Append to the modal body
      const modalBody = this.modal.querySelector('.receipt-modal-body');
      modalBody.appendChild(studentInfoContainer);
    }
    
    const student = this.studentInfo;
    studentInfoContainer.innerHTML = `
      <div style="display: flex; align-items: center; margin-bottom: 0.75rem;">
        <i class="fas fa-user" style="color: #2563eb; margin-right: 0.5rem; font-size: 0.875rem;"></i>
        <h5 style="margin: 0; color: #0f172a; font-size: 0.875rem; font-weight: 600;">Student Information</h5>
      </div>
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; font-size: 0.8125rem;">
        <div>
          <span style="color: #64748b; font-weight: 500;">Name:</span>
          <div style="color: #0f172a; font-weight: 600;">${student.full_name || '—'}</div>
        </div>
        <div>
          <span style="color: #64748b; font-weight: 500;">Student ID:</span>
          <div style="color: #0f172a; font-weight: 600;">${student.student_id || '—'}</div>
        </div>
        <div>
          <span style="color: #64748b; font-weight: 500;">Course:</span>
          <div style="color: #0f172a; font-weight: 600;">${student.course_name || '—'}</div>
        </div>
        <div>
          <span style="color: #64748b; font-weight: 500;">Year Level:</span>
          <div style="color: #0f172a; font-weight: 600;">${student.year_level_name || student.year_level || '—'}</div>
        </div>
      </div>
    `;
    
    studentInfoContainer.style.display = 'block';
  }

  hideAllStates() {
    const states = ['#receipt-loading', '#receipt-error', '#receipt-no-image', '#receipt-image-container', '#receipt-payment-info', '#receipt-student-info'];
    states.forEach(selector => {
      const element = this.modal.querySelector(selector);
      if (element) {
        element.style.display = 'none';
      }
    });
  }

  toggleZoom() {
    if (!this.currentImage) return;
    
    const isZoomed = this.currentImage.classList.contains('zoomed');
    const zoomBtn = this.modal.querySelector('#receipt-zoom-btn');
    const icon = zoomBtn.querySelector('i');
    
    if (isZoomed) {
      this.currentImage.classList.remove('zoomed');
      icon.className = 'fas fa-search-plus';
      zoomBtn.innerHTML = '<i class="fas fa-search-plus"></i> Zoom';
    } else {
      this.currentImage.classList.add('zoomed');
      icon.className = 'fas fa-search-minus';
      zoomBtn.innerHTML = '<i class="fas fa-search-minus"></i> Unzoom';
    }
  }

  downloadImage() {
    if (!this.currentImage || !this.currentImage.src) return;
    
    try {
      const link = document.createElement('a');
      link.href = this.currentImage.src;
      link.download = `receipt-${Date.now()}.jpg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Download failed:', error);
      // Fallback: open in new tab
      window.open(this.currentImage.src, '_blank');
    }
  }

  close() {
    this.isOpen = false;
    this.modal.classList.remove('show');
    
    // Reset zoom state
    if (this.currentImage) {
      this.currentImage.classList.remove('zoomed');
    }
    
    // Reset button state
    const zoomBtn = this.modal.querySelector('#receipt-zoom-btn');
    if (zoomBtn) {
      zoomBtn.innerHTML = '<i class="fas fa-search-plus"></i> Zoom';
    }
  }
}

// Utility function for easy use
window.showReceiptModal = function(requestId) {
  console.log('🔍 Receipt Modal: showReceiptModal called with requestId:', requestId);
  console.log('🔍 Receipt Modal: requestId type:', typeof requestId);
  console.log('🔍 Receipt Modal: requestId value:', requestId);
  
  if (!window.receiptModal) {
    console.log('🔍 Receipt Modal: Creating new ReceiptModal instance');
    window.receiptModal = new ReceiptModal();
  }
  
  // Ensure the modal is initialized
  if (!window.receiptModal.initialized) {
    console.log('🔍 Receipt Modal: Initializing modal...');
    window.receiptModal.initializeModal();
  }
  
  console.log('🔍 Receipt Modal: Calling modal.show()');
  window.receiptModal.show(requestId);
};

// Initialize when DOM is ready
function initializeReceiptModal() {
  if (!window.receiptModal) {
    window.receiptModal = new ReceiptModal();
  }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeReceiptModal);
} else {
  initializeReceiptModal();
}
