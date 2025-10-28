/**
 * Universal Loading Utility for Buttons
 * Provides loading states for all buttons that trigger async operations
 */

class ButtonLoadingManager {
  constructor() {
    this.loadingButtons = new Map();
    this.originalStates = new Map();
  }

  /**
   * Show loading state on a button
   * @param {HTMLElement} button - The button element
   * @param {string} loadingText - Text to show during loading (optional)
   * @param {boolean} showSpinner - Whether to show spinner (default: true)
   */
  showLoading(button, loadingText = 'Loading...', showSpinner = true) {
    if (!button || this.loadingButtons.has(button)) return;

    // Store original state
    const originalState = {
      innerHTML: button.innerHTML,
      disabled: button.disabled,
      classList: Array.from(button.classList),
      style: button.style.cssText
    };
    this.originalStates.set(button, originalState);

    // Mark as loading
    this.loadingButtons.set(button, true);

    // Disable button
    button.disabled = true;
    button.style.pointerEvents = 'none';
    button.style.opacity = '0.7';

    // Create professional skeleton loading content
    let loadingContent = '';
    if (showSpinner) {
      loadingContent = `
        <div class="button-skeleton">
          <div class="skeleton-text-line"></div>
          <svg class="button-spinner" viewBox="0 0 100 101" fill="none">
            <path d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z" fill="currentColor"/>
            <path d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z" fill="currentFill"/>
          </svg>
        </div>
      `;
    } else {
      loadingContent = loadingText;
    }

    // Update button content
    button.innerHTML = loadingContent;

    // Add loading class for styling
    button.classList.add('btn-loading');
  }

  /**
   * Hide loading state and restore original button state
   * @param {HTMLElement} button - The button element
   */
  hideLoading(button) {
    if (!button || !this.loadingButtons.has(button)) return;

    // Remove loading state
    this.loadingButtons.delete(button);

    // Restore original state
    const originalState = this.originalStates.get(button);
    if (originalState) {
      button.innerHTML = originalState.innerHTML;
      button.disabled = originalState.disabled;
      button.style.cssText = originalState.style;
      button.classList.remove('btn-loading');
      this.originalStates.delete(button);
    }
  }

  /**
   * Check if button is currently in loading state
   * @param {HTMLElement} button - The button element
   * @returns {boolean}
   */
  isLoading(button) {
    return this.loadingButtons.has(button);
  }

  /**
   * Wrapper function to execute async operation with loading state
   * @param {HTMLElement} button - The button element
   * @param {Function} asyncFunction - The async function to execute
   * @param {string} loadingText - Text to show during loading
   * @param {boolean} showSpinner - Whether to show spinner
   */
  async executeWithLoading(button, asyncFunction, loadingText = 'Loading...', showSpinner = true) {
    if (this.isLoading(button)) return;

    try {
      this.showLoading(button, loadingText, showSpinner);
      const result = await asyncFunction();
      return result;
    } catch (error) {
      console.error('Error in async operation:', error);
      throw error;
    } finally {
      this.hideLoading(button);
    }
  }

  /**
   * Auto-detect buttons with async onclick handlers and wrap them
   */
  autoWrapAsyncButtons() {
    // Find all buttons with onclick handlers
    const buttons = document.querySelectorAll('button[onclick]');
    
    buttons.forEach(button => {
      const originalOnclick = button.getAttribute('onclick');
      
      // Check if the onclick handler calls an async function
      if (this.isAsyncFunction(originalOnclick)) {
        button.removeAttribute('onclick');
        button.addEventListener('click', async (e) => {
          e.preventDefault();
          await this.executeWithLoading(button, async () => {
            // Execute the original onclick function
            return eval(originalOnclick);
          });
        });
      }
    });
  }

  /**
   * Show full-screen loading overlay
   * @param {string} loadingText - Text to show during loading
   */
  showFullScreenLoading(loadingText = 'Loading...') {
    // Remove any existing full-screen loading
    this.hideFullScreenLoading();

    // Create full-screen loading overlay
    const overlay = document.createElement('div');
    overlay.id = 'fullscreen-loading-overlay';
    overlay.className = 'fullscreen-loading-overlay';
    
    overlay.innerHTML = `
      <div class="fullscreen-loading-content">
        <div class="fullscreen-loading-spinner">
          <svg class="loading-spinner-svg" viewBox="0 0 100 101" fill="none">
            <path d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z" fill="currentColor"/>
            <path d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z" fill="currentFill"/>
          </svg>
        </div>
        <div class="fullscreen-loading-text">${loadingText}</div>
        <div class="fullscreen-loading-subtitle">Please wait while we process your request...</div>
      </div>
    `;

    // Add to body
    document.body.appendChild(overlay);
    
    // Prevent body scroll
    document.body.style.overflow = 'hidden';
  }

  /**
   * Hide full-screen loading overlay
   */
  hideFullScreenLoading() {
    const overlay = document.getElementById('fullscreen-loading-overlay');
    if (overlay) {
      overlay.remove();
    }
    
    // Restore body scroll
    document.body.style.overflow = '';
  }

  /**
   * Check if a function string is likely async
   * @param {string} functionString - The function string to check
   * @returns {boolean}
   */
  isAsyncFunction(functionString) {
    const asyncKeywords = [
      'submitRequest', 'loadRequests', 'viewDetails', 'approveClearance',
      'rejectClearance', 'uploadFile', 'saveFile', 'processRequest',
      'updateStatus', 'sendMessage', 'fetchData', 'submitForm'
    ];
    
    return asyncKeywords.some(keyword => 
      functionString.toLowerCase().includes(keyword.toLowerCase())
    );
  }
}

// Global instance
window.buttonLoadingManager = new ButtonLoadingManager();

// Professional Skeleton Loading CSS
const loadingStyles = `
  /* Professional Skeleton Loading Animations */
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
  
  @keyframes shimmer {
    0% { background-position: -200px 0; }
    100% { background-position: calc(200px + 100%) 0; }
  }
  
  @keyframes pulse {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 0.8; }
  }
  
  /* Button Loading Styles */
  .btn-loading {
    position: relative;
    cursor: not-allowed !important;
    opacity: 0.7;
  }
  
  .btn-loading:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
  
  .button-skeleton {
    display: flex;
    align-items: center;
    gap: 8px;
    opacity: 0.6;
  }
  
  .skeleton-text-line {
    width: 60px;
    height: 16px;
    background: #e5e7eb;
    border-radius: 4px;
    animation: shimmer 1.5s infinite;
  }
  
  .button-spinner {
    width: 16px;
    height: 16px;
    color: #6b7280;
    animation: spin 1s linear infinite;
  }
  
  /* Card Loading Styles - Professional Skeleton */
  .card-loading {
    position: relative;
    cursor: not-allowed !important;
    transform: none !important;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    opacity: 0.8;
  }
  
  .card-loading:hover {
    transform: none !important;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1) !important;
  }
  
  .skeleton-badge {
    position: absolute;
    top: 12px;
    right: 12px;
    width: 40px;
    height: 20px;
    background: #e5e7eb;
    border-radius: 4px;
    animation: shimmer 1.5s infinite;
  }
  
  .skeleton-text-small {
    width: 100%;
    height: 100%;
    background: #d1d5db;
    border-radius: 4px;
  }
  
  .skeleton-icon {
    width: 60px;
    height: 60px;
    border-radius: 12px;
    background: #e5e7eb;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 12px;
    animation: shimmer 1.5s infinite;
  }
  
  .skeleton-circle {
    width: 24px;
    height: 24px;
    background: #d1d5db;
    border-radius: 50%;
  }
  
  .skeleton-content {
    flex: 1;
  }
  
  .skeleton-title {
    width: 80%;
    height: 24px;
    background: #e5e7eb;
    border-radius: 4px;
    margin-bottom: 8px;
    animation: shimmer 1.5s infinite;
  }
  
  .skeleton-subtitle {
    width: 100%;
    height: 16px;
    background: #e5e7eb;
    border-radius: 4px;
    animation: shimmer 1.5s infinite;
  }
  
  .skeleton-loader {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 10;
  }
  
  .skeleton-spinner {
    width: 32px;
    height: 32px;
    color: #6b7280;
    animation: spin 1s linear infinite;
  }
  
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
  
  /* Full-Screen Loading Overlay */
  .fullscreen-loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(255, 255, 255, 0.3);
    backdrop-filter: blur(2px);
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.3s ease-in-out;
  }
  
  .fullscreen-loading-content {
    text-align: center;
    max-width: 400px;
    padding: 2rem;
    background: rgba(255, 255, 255, 0.8);
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }
  
  .fullscreen-loading-spinner {
    margin-bottom: 1.5rem;
  }
  
  .loading-spinner-svg {
    width: 48px;
    height: 48px;
    color: #3b82f6;
    animation: spin 1s linear infinite;
  }
  
  .fullscreen-loading-text {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1f2937;
    margin-bottom: 0.5rem;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  }
  
  .fullscreen-loading-subtitle {
    font-size: 1rem;
    color: #4b5563;
    font-weight: 500;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  }
  
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
`;

// Inject styles
const styleSheet = document.createElement('style');
styleSheet.textContent = loadingStyles;
document.head.appendChild(styleSheet);

// Utility functions for easy use
window.showButtonLoading = (button, text = 'Loading...', showSpinner = true) => {
  window.buttonLoadingManager.showLoading(button, text, showSpinner);
};

window.hideButtonLoading = (button) => {
  window.buttonLoadingManager.hideLoading(button);
};

window.executeWithButtonLoading = async (button, asyncFunction, loadingText = 'Loading...', showSpinner = true) => {
  return await window.buttonLoadingManager.executeWithLoading(button, asyncFunction, loadingText, showSpinner);
};

// Card loading utility functions
window.showCardLoading = (card, text = 'Loading...') => {
  window.buttonLoadingManager.showCardLoading(card, text);
};

window.hideCardLoading = (card) => {
  window.buttonLoadingManager.hideCardLoading(card);
};

window.executeWithCardLoading = async (card, asyncFunction, loadingText = 'Loading...') => {
  try {
    window.buttonLoadingManager.showCardLoading(card, loadingText);
    const result = await asyncFunction();
    return result;
  } catch (error) {
    console.error('Error in card async operation:', error);
    throw error;
  } finally {
    window.buttonLoadingManager.hideCardLoading(card);
  }
};

// Full-screen loading utility functions
window.showFullScreenLoading = (text = 'Loading...') => {
  window.buttonLoadingManager.showFullScreenLoading(text);
};

window.hideFullScreenLoading = () => {
  window.buttonLoadingManager.hideFullScreenLoading();
};

window.executeWithFullScreenLoading = async (asyncFunction, loadingText = 'Loading...') => {
  try {
    window.buttonLoadingManager.showFullScreenLoading(loadingText);
    const result = await asyncFunction();
    return result;
  } catch (error) {
    console.error('Error in full-screen async operation:', error);
    throw error;
  } finally {
    window.buttonLoadingManager.hideFullScreenLoading();
  }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Auto-wrap async buttons
  window.buttonLoadingManager.autoWrapAsyncButtons();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ButtonLoadingManager;
}
