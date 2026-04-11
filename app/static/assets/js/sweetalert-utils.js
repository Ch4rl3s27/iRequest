/**
 * Professional SweetAlert2 Utility Functions
 * Provides consistent, professional alert styling across the iRequest application
 */

// ===== CONFIGURATION =====
const SWEETALERT_CONFIG = {
  // Default settings for all alerts
  default: {
    allowOutsideClick: false,
    allowEscapeKey: true,
    showCloseButton: true,
    showConfirmButton: true,
    confirmButtonText: 'OK',
    confirmButtonColor: '#3b82f6',
    cancelButtonColor: '#6b7280',
    denyButtonColor: '#ef4444',
    focusConfirm: true,
    reverseButtons: false,
    customClass: {
      popup: 'swal2-professional-popup',
      title: 'swal2-professional-title',
      content: 'swal2-professional-content',
      confirmButton: 'swal2-professional-confirm',
      cancelButton: 'swal2-professional-cancel',
      denyButton: 'swal2-professional-deny'
    }
  },
  
  // Animation settings
  animation: {
    show: {
      animation: 'swal2-show',
      duration: 300
    },
    hide: {
      animation: 'swal2-hide',
      duration: 300
    }
  }
};

// ===== UTILITY FUNCTIONS =====

/**
 * Show a success alert with professional styling
 * @param {string} title - Alert title
 * @param {string} text - Alert message
 * @param {Object} options - Additional SweetAlert options
 * @returns {Promise} SweetAlert result
 */
function showSuccessAlert(title, text, options = {}) {
  return Swal.fire({
    ...SWEETALERT_CONFIG.default,
    title: title,
    text: text,
    icon: 'success',
    iconColor: '#10b981',
    confirmButtonText: options.confirmButtonText || 'Great!',
    confirmButtonColor: '#10b981',
    ...options
  });
}

/**
 * Show an error alert with professional styling
 * @param {string} title - Alert title
 * @param {string} text - Alert message
 * @param {Object} options - Additional SweetAlert options
 * @returns {Promise} SweetAlert result
 */
function showErrorAlert(title, text, options = {}) {
  return Swal.fire({
    ...SWEETALERT_CONFIG.default,
    title: title,
    text: text,
    icon: 'error',
    iconColor: '#ef4444',
    confirmButtonText: options.confirmButtonText || 'Try Again',
    confirmButtonColor: '#ef4444',
    ...options
  });
}

/**
 * Show a warning alert with professional styling
 * @param {string} title - Alert title
 * @param {string} text - Alert message
 * @param {Object} options - Additional SweetAlert options
 * @returns {Promise} SweetAlert result
 */
function showWarningAlert(title, text, options = {}) {
  return Swal.fire({
    ...SWEETALERT_CONFIG.default,
    title: title,
    text: text,
    icon: 'warning',
    iconColor: '#f59e0b',
    confirmButtonText: options.confirmButtonText || 'Got it',
    confirmButtonColor: '#f59e0b',
    ...options
  });
}

/**
 * Show an info alert with professional styling
 * @param {string} title - Alert title
 * @param {string} text - Alert message
 * @param {Object} options - Additional SweetAlert options
 * @returns {Promise} SweetAlert result
 */
function showInfoAlert(title, text, options = {}) {
  return Swal.fire({
    ...SWEETALERT_CONFIG.default,
    title: title,
    text: text,
    icon: 'info',
    iconColor: '#3b82f6',
    confirmButtonText: options.confirmButtonText || 'OK',
    confirmButtonColor: '#3b82f6',
    ...options
  });
}

/**
 * Show a confirmation dialog with professional styling
 * @param {string} title - Dialog title
 * @param {string} text - Dialog message
 * @param {Object} options - Additional SweetAlert options
 * @returns {Promise} SweetAlert result
 */
function showConfirmDialog(title, text, options = {}) {
  return Swal.fire({
    ...SWEETALERT_CONFIG.default,
    title: title,
    text: text,
    icon: 'question',
    iconColor: '#8b5cf6',
    showCancelButton: true,
    confirmButtonText: options.confirmButtonText || 'Yes, continue',
    cancelButtonText: options.cancelButtonText || 'Cancel',
    confirmButtonColor: '#3b82f6',
    cancelButtonColor: '#6b7280',
    focusConfirm: true,
    reverseButtons: true,
    ...options
  });
}

/**
 * Show a loading alert with professional styling
 * @param {string} title - Loading title
 * @param {string} text - Loading message
 * @param {Object} options - Additional SweetAlert options
 * @returns {Promise} SweetAlert result
 */
function showLoadingAlert(title, text, options = {}) {
  return Swal.fire({
    title: title,
    text: text,
    allowOutsideClick: false,
    allowEscapeKey: false,
    showConfirmButton: false,
    showCancelButton: false,
    showCloseButton: false,
    didOpen: () => {
      Swal.showLoading();
    },
    ...options
  });
}

/**
 * Show a custom HTML alert with professional styling
 * @param {string} title - Alert title
 * @param {string} html - HTML content
 * @param {string} icon - Icon type (success, error, warning, info, question)
 * @param {Object} options - Additional SweetAlert options
 * @returns {Promise} SweetAlert result
 */
function showCustomAlert(title, html, icon = 'info', options = {}) {
  const iconColors = {
    success: '#10b981',
    error: '#ef4444',
    warning: '#f59e0b',
    info: '#3b82f6',
    question: '#8b5cf6'
  };

  return Swal.fire({
    ...SWEETALERT_CONFIG.default,
    title: title,
    html: html,
    icon: icon,
    iconColor: iconColors[icon] || '#3b82f6',
    ...options
  });
}

/**
 * Show a toast notification with professional styling
 * @param {string} title - Toast title
 * @param {string} text - Toast message
 * @param {string} icon - Icon type
 * @param {Object} options - Additional SweetAlert options
 * @returns {Promise} SweetAlert result
 */
function showToast(title, text, icon = 'success', options = {}) {
  const iconColors = {
    success: '#10b981',
    error: '#ef4444',
    warning: '#f59e0b',
    info: '#3b82f6'
  };

  return Swal.fire({
    title: title,
    text: text,
    icon: icon,
    iconColor: iconColors[icon] || '#3b82f6',
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: options.timer || 3000,
    timerProgressBar: true,
    didOpen: (toast) => {
      toast.addEventListener('mouseenter', Swal.stopTimer);
      toast.addEventListener('mouseleave', Swal.resumeTimer);
    },
    ...options
  });
}

/**
 * Show a form input alert with professional styling
 * @param {string} title - Alert title
 * @param {string} text - Alert message
 * @param {string} inputType - Input type (text, email, password, number, etc.)
 * @param {Object} options - Additional SweetAlert options
 * @returns {Promise} SweetAlert result
 */
function showInputAlert(title, text, inputType = 'text', options = {}) {
  return Swal.fire({
    ...SWEETALERT_CONFIG.default,
    title: title,
    text: text,
    input: inputType,
    inputPlaceholder: options.inputPlaceholder || 'Enter value...',
    inputValidator: options.inputValidator,
    showCancelButton: true,
    confirmButtonText: options.confirmButtonText || 'Submit',
    cancelButtonText: options.cancelButtonText || 'Cancel',
    confirmButtonColor: '#3b82f6',
    cancelButtonColor: '#6b7280',
    ...options
  });
}

/**
 * Show a file upload alert with professional styling
 * @param {string} title - Alert title
 * @param {string} text - Alert message
 * @param {Object} options - Additional SweetAlert options
 * @returns {Promise} SweetAlert result
 */
function showFileUploadAlert(title, text, options = {}) {
  return Swal.fire({
    ...SWEETALERT_CONFIG.default,
    title: title,
    text: text,
    input: 'file',
    inputAttributes: options.inputAttributes || {
      accept: 'image/*,.pdf,.doc,.docx',
      'aria-label': 'Upload your file'
    },
    showCancelButton: true,
    confirmButtonText: options.confirmButtonText || 'Upload',
    cancelButtonText: options.cancelButtonText || 'Cancel',
    confirmButtonColor: '#3b82f6',
    cancelButtonColor: '#6b7280',
    ...options
  });
}

/**
 * Show a select dropdown alert with professional styling
 * @param {string} title - Alert title
 * @param {string} text - Alert message
 * @param {Array} inputOptions - Select options
 * @param {Object} options - Additional SweetAlert options
 * @returns {Promise} SweetAlert result
 */
function showSelectAlert(title, text, inputOptions, options = {}) {
  return Swal.fire({
    ...SWEETALERT_CONFIG.default,
    title: title,
    text: text,
    input: 'select',
    inputOptions: inputOptions,
    inputPlaceholder: options.inputPlaceholder || 'Select an option...',
    showCancelButton: true,
    confirmButtonText: options.confirmButtonText || 'Select',
    cancelButtonText: options.cancelButtonText || 'Cancel',
    confirmButtonColor: '#3b82f6',
    cancelButtonColor: '#6b7280',
    ...options
  });
}

/**
 * Show a textarea alert with professional styling
 * @param {string} title - Alert title
 * @param {string} text - Alert message
 * @param {Object} options - Additional SweetAlert options
 * @returns {Promise} SweetAlert result
 */
function showTextareaAlert(title, text, options = {}) {
  return Swal.fire({
    ...SWEETALERT_CONFIG.default,
    title: title,
    text: text,
    input: 'textarea',
    inputPlaceholder: options.inputPlaceholder || 'Enter your message...',
    inputAttributes: {
      'aria-label': 'Type your message here'
    },
    showCancelButton: true,
    confirmButtonText: options.confirmButtonText || 'Send',
    cancelButtonText: options.cancelButtonText || 'Cancel',
    confirmButtonColor: '#3b82f6',
    cancelButtonColor: '#6b7280',
    ...options
  });
}

/**
 * Close any open SweetAlert
 */
function closeAlert() {
  Swal.close();
}

/**
 * Update the content of an open SweetAlert
 * @param {Object} options - New content options
 */
function updateAlert(options) {
  Swal.update(options);
}

/**
 * Show a progress alert with professional styling
 * @param {string} title - Alert title
 * @param {string} text - Alert message
 * @param {number} progress - Progress percentage (0-100)
 * @param {Object} options - Additional SweetAlert options
 * @returns {Promise} SweetAlert result
 */
function showProgressAlert(title, text, progress = 0, options = {}) {
  return Swal.fire({
    title: title,
    text: text,
    allowOutsideClick: false,
    allowEscapeKey: false,
    showConfirmButton: false,
    showCancelButton: false,
    showCloseButton: false,
    didOpen: () => {
      Swal.showLoading();
      if (progress > 0) {
        Swal.getProgressSteps().style.display = 'block';
        Swal.getProgressSteps().style.width = `${progress}%`;
      }
    },
    ...options
  });
}

// ===== SPECIALIZED ALERTS FOR iREQUEST =====

/**
 * Show a session expired alert
 * @param {Function} onConfirm - Callback when user confirms
 */
function showSessionExpiredAlert(onConfirm) {
  return showWarningAlert(
    'Session Expired',
    'Your session has expired. Please log in again to continue.',
    {
      confirmButtonText: 'Login Again',
      allowOutsideClick: false,
      allowEscapeKey: false,
      didClose: onConfirm
    }
  );
}

/**
 * Show a network error alert
 * @param {Function} onRetry - Callback when user retries
 */
function showNetworkErrorAlert(onRetry) {
  return showErrorAlert(
    'Network Error',
    'Unable to connect to the server. Please check your internet connection and try again.',
    {
      confirmButtonText: 'Retry',
      showCancelButton: true,
      cancelButtonText: 'Cancel',
      didClose: (result) => {
        if (result.isConfirmed && onRetry) {
          onRetry();
        }
      }
    }
  );
}

/**
 * Show a form validation error alert
 * @param {string} message - Validation error message
 */
function showValidationErrorAlert(message) {
  return showWarningAlert(
    'Validation Error',
    message,
    {
      confirmButtonText: 'Fix Now'
    }
  );
}

/**
 * Show a success toast for form submissions
 * @param {string} message - Success message
 */
function showFormSuccessToast(message) {
  return showToast(
    'Success!',
    message,
    'success',
    {
      timer: 2000,
      position: 'top-end'
    }
  );
}

/**
 * Show an error toast for form submissions
 * @param {string} message - Error message
 */
function showFormErrorToast(message) {
  return showToast(
    'Error',
    message,
    'error',
    {
      timer: 4000,
      position: 'top-end'
    }
  );
}

// ===== EXPORT FUNCTIONS (for module usage) =====
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    showSuccessAlert,
    showErrorAlert,
    showWarningAlert,
    showInfoAlert,
    showConfirmDialog,
    showLoadingAlert,
    showCustomAlert,
    showToast,
    showInputAlert,
    showFileUploadAlert,
    showSelectAlert,
    showTextareaAlert,
    closeAlert,
    updateAlert,
    showProgressAlert,
    showSessionExpiredAlert,
    showNetworkErrorAlert,
    showValidationErrorAlert,
    showFormSuccessToast,
    showFormErrorToast,
    SWEETALERT_CONFIG
  };
}

// ===== GLOBAL AVAILABILITY =====
// Make functions available globally for easy use in HTML files
window.SweetAlertUtils = {
  success: showSuccessAlert,
  error: showErrorAlert,
  warning: showWarningAlert,
  info: showInfoAlert,
  confirm: showConfirmDialog,
  loading: showLoadingAlert,
  custom: showCustomAlert,
  toast: showToast,
  input: showInputAlert,
  fileUpload: showFileUploadAlert,
  select: showSelectAlert,
  textarea: showTextareaAlert,
  close: closeAlert,
  update: updateAlert,
  progress: showProgressAlert,
  sessionExpired: showSessionExpiredAlert,
  networkError: showNetworkErrorAlert,
  validationError: showValidationErrorAlert,
  formSuccess: showFormSuccessToast,
  formError: showFormErrorToast
};
