/**
 * Enhanced GTIN Input Component
 * Combines GTIN parsing with barcode scanning functionality
 */

class GTINInputComponent {
  constructor(options = {}) {
    this.gtinInput = options.gtinInput;
    this.lotInput = options.lotInput;
    this.expirationInput = options.expirationInput;
    this.onParsed = options.onParsed || (() => {});
    this.showNotifications = options.showNotifications !== false;
    
    this.scannerButton = null;
    this.parseTimeout = null;
    
    this.init();
  }

  /**
   * Initialize the component
   */
  init() {
    if (!this.gtinInput) {
      console.error('GTIN input element is required');
      return;
    }

    this.setupGTINInput();
    this.createScannerButton();
    this.attachEventListeners();
  }

  /**
   * Setup the GTIN input field
   */
  setupGTINInput() {
    // Add some styling and attributes
    this.gtinInput.setAttribute('autocomplete', 'off');
    this.gtinInput.setAttribute('placeholder', 'Enter GTIN or scan barcode');
    
    // Create container for input group if not exists
    if (!this.gtinInput.parentElement.classList.contains('input-group')) {
      const wrapper = document.createElement('div');
      wrapper.className = 'input-group';
      this.gtinInput.parentNode.insertBefore(wrapper, this.gtinInput);
      wrapper.appendChild(this.gtinInput);
    }
  }

  /**
   * Create the scanner button
   */
  createScannerButton() {
    const inputGroup = this.gtinInput.closest('.input-group');
    if (!inputGroup) return;

    // Show scanner button if scanner is available and supported
    const scanner = window.BarcodeScanner;
    if (!scanner || !scanner.isSupported()) {
      return;
    }

    this.scannerButton = document.createElement('button');
    this.scannerButton.type = 'button';
    this.scannerButton.className = 'btn btn-outline-secondary';
    this.scannerButton.innerHTML = `
      <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
        <path d="M1.5 1a.5.5 0 0 0-.5.5v3a.5.5 0 0 1-1 0v-3A1.5 1.5 0 0 1 1.5 0h3a.5.5 0 0 1 0 1h-3zM11 .5a.5.5 0 0 1 .5-.5h3A1.5 1.5 0 0 1 16 1.5v3a.5.5 0 0 1-1 0v-3a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 1-.5-.5zM.5 11a.5.5 0 0 1 .5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 1 0 1h-3A1.5 1.5 0 0 1 0 14.5v-3a.5.5 0 0 1 .5-.5zm15 0a.5.5 0 0 1 .5.5v3a1.5 1.5 0 0 1-1.5 1.5h-3a.5.5 0 0 1 0-1h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 1 .5-.5zM3 4.5a.5.5 0 0 1 1 0v7a.5.5 0 0 1-1 0v-7zm2 0a.5.5 0 0 1 1 0v7a.5.5 0 0 1-1 0v-7zm2 0a.5.5 0 0 1 1 0v7a.5.5 0 0 1-1 0v-7zm2 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0v-6a.5.5 0 0 1 .5-.5zm3 0a.5.5 0 0 1 1 0v7a.5.5 0 0 1-1 0v-7z"/>
      </svg>
    `;
    this.scannerButton.title = 'Scan barcode with camera';

    // Add scanner button to input group
    inputGroup.appendChild(this.scannerButton);
  }

  /**
   * Attach event listeners
   */
  attachEventListeners() {
    // GTIN input blur event for parsing
    this.gtinInput.addEventListener('blur', this.handleGTINBlur.bind(this));
    
    // Scanner button click
    if (this.scannerButton) {
      this.scannerButton.addEventListener('click', this.handleScannerClick.bind(this));
    }

    // Also parse on paste
    this.gtinInput.addEventListener('paste', (e) => {
      setTimeout(() => this.handleGTINBlur(), 100);
    });
  }

  /**
   * Handle GTIN input blur (when user clicks away)
   */
  handleGTINBlur() {
    const value = this.gtinInput.value.trim();
    if (!value) return;

    // Clear any pending parse
    if (this.parseTimeout) {
      clearTimeout(this.parseTimeout);
    }

    // Parse after a short delay to ensure the value is finalized
    this.parseTimeout = setTimeout(() => {
      this.parseGTIN(value);
    }, 100);
  }

  /**
   * Handle scanner button click
   */
  handleScannerClick() {
    const scanner = window.BarcodeScanner;
    if (!scanner) {
      this.showError('Barcode scanner not available');
      return;
    }

    if (!scanner.isSupported()) {
      this.showError('Camera not supported on this device');
      return;
    }

    scanner.showScannerModal(
      (code) => {
        this.gtinInput.value = code;
        this.parseGTIN(code);
        this.showSuccess('Barcode scanned successfully');
      },
      (error) => {
        this.showError(`Scanner error: ${error.message}`);
      }
    );
  }

  /**
   * Parse GTIN value and populate related fields
   * @param {string} value - The GTIN value to parse
   */
  parseGTIN(value) {
    const parser = window.GTINParser;
    if (!parser) {
      console.error('GTIN Parser not available');
      return;
    }

    const parsed = parser.parseBarcode(value);
    
    // Update GTIN field with clean GTIN
    if (parsed.gtin && parsed.gtin !== value) {
      this.gtinInput.value = parsed.gtin;
    }

    // Populate lot field if available and lot input exists
    if (parsed.lot && this.lotInput) {
      const currentLot = this.lotInput.value.trim();
      if (!currentLot || confirm('Replace existing lot number with scanned value?')) {
        this.lotInput.value = parsed.lot;
        this.highlightField(this.lotInput);
      }
    }

    // Populate expiration field if available and expiration input exists
    if (parsed.expiration && this.expirationInput) {
      const currentExpiration = this.expirationInput.value.trim();
      if (!currentExpiration || confirm('Replace existing expiration date with scanned value?')) {
        this.expirationInput.value = parsed.expiration;
        this.highlightField(this.expirationInput);
      }
    }

    // Show notification if GS1 data was parsed
    if (parsed.isGS1 && this.showNotifications) {
      const items = [];
      if (parsed.gtin) items.push('GTIN');
      if (parsed.lot) items.push('Lot');
      if (parsed.expiration) items.push('Expiration');
      
      if (items.length > 1) {
        this.showSuccess(`Parsed GS1 barcode: ${items.join(', ')}`);
      }
    }

    // Show errors if any
    if (parsed.errors && parsed.errors.length > 0) {
      parsed.errors.forEach(error => this.showWarning(error));
    }

    // Call callback
    this.onParsed(parsed);
  }

  /**
   * Highlight a field briefly to show it was auto-filled
   * @param {HTMLElement} field - The field to highlight
   */
  highlightField(field) {
    const originalBackground = field.style.backgroundColor;
    field.style.backgroundColor = '#d4edda';
    field.style.transition = 'background-color 0.3s ease';
    
    setTimeout(() => {
      field.style.backgroundColor = originalBackground;
      setTimeout(() => {
        field.style.transition = '';
      }, 300);
    }, 1000);
  }

  /**
   * Show success notification
   * @param {string} message - The message to show
   */
  showSuccess(message) {
    this.showNotification(message, 'success');
  }

  /**
   * Show error notification
   * @param {string} message - The message to show
   */
  showError(message) {
    this.showNotification(message, 'error');
  }

  /**
   * Show warning notification
   * @param {string} message - The message to show
   */
  showWarning(message) {
    this.showNotification(message, 'warning');
  }

  /**
   * Show notification (basic implementation)
   * @param {string} message - The message to show
   * @param {string} type - The type of notification
   */
  showNotification(message, type = 'info') {
    // Use browser notification or fallback to alert
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('GTIN Scanner', { body: message });
    } else {
      // Simple toast-like notification using Bootstrap 4
      const toast = document.createElement('div');
      toast.className = `alert alert-${type === 'error' ? 'danger' : type === 'warning' ? 'warning' : 'success'} alert-dismissible fade show`;
      toast.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
      toast.innerHTML = `
        ${message}
        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
          <span aria-hidden="true">&times;</span>
        </button>
      `;
      
      document.body.appendChild(toast);
      
      // Auto remove after 5 seconds
      setTimeout(() => {
        if (toast.parentNode) {
          toast.remove();
        }
      }, 5000);

      // Handle close button with Bootstrap 4
      const closeBtn = toast.querySelector('.close');
      if (closeBtn) {
        closeBtn.addEventListener('click', () => toast.remove());
      }
    }
  }

  /**
   * Destroy the component
   */
  destroy() {
    if (this.parseTimeout) {
      clearTimeout(this.parseTimeout);
    }
    
    if (this.scannerButton && this.scannerButton.parentNode) {
      this.scannerButton.remove();
    }
  }
}

// Make available globally
window.GTINInputComponent = GTINInputComponent;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = GTINInputComponent;
}