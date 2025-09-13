/**
 * Barcode Scanner and GS1 Parser Module
 * Provides functionality for parsing GS1 Application Identifiers and camera-based barcode scanning
 * Uses quagga2 library for reliable barcode detection
 */

class BarcodeScanner {
    constructor() {
        this.container = null;
        this.isScanning = false;
        this.onResult = null;
        this.isQuaggaLoaded = false;
        this.loadQuaggaPromise = null;
        this.torchSupported = false;
        this.torchEnabled = false;
    }

    /**
     * Parse GS1 Application Identifiers from a barcode string
     * Supports (01) GTIN, (10) Lot, (17) Expiration
     */
    static parseGS1(barcodeData) {
        if (!barcodeData || typeof barcodeData !== 'string') {
            return { gtin: barcodeData || '', lot: '', expiration: '' };
        }

        // Remove any whitespace
        const data = barcodeData.trim();
        
        // Check if this looks like GS1 data (contains parentheses with numbers)
        const gs1Pattern = /\((\d{2,4})\)([^(]*)/g;
        const matches = [...data.matchAll(gs1Pattern)];
        
        if (matches.length === 0) {
            // No GS1 identifiers found, treat as plain GTIN
            return { gtin: data, lot: '', expiration: '' };
        }

        const result = { gtin: '', lot: '', expiration: '' };
        
        for (const match of matches) {
            const identifier = match[1];
            const value = match[2].trim();
            
            switch (identifier) {
                case '01':  // GTIN
                    result.gtin = value;
                    break;
                case '10':  // Lot/Batch Number
                    result.lot = value;
                    break;
                case '17':  // Expiration Date (YYMMDD)
                    result.expiration = this.parseGS1Date(value);
                    break;
            }
        }
        
        return result;
    }

    /**
     * Parse GS1 date format (YYMMDD) to YYYY-MM-DD
     */
    static parseGS1Date(dateStr) {
        if (!dateStr || dateStr.length !== 6) {
            return '';
        }
        
        try {
            const year = parseInt(dateStr.substring(0, 2));
            const month = parseInt(dateStr.substring(2, 4));
            const day = parseInt(dateStr.substring(4, 6));
            
            // Assume years 00-30 are 2000-2030, 31-99 are 1931-1999
            const fullYear = year <= 30 ? 2000 + year : 1900 + year;
            
            // Validate month and day
            if (month < 1 || month > 12 || day < 1 || day > 31) {
                return '';
            }
            
            return `${fullYear}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
        } catch (e) {
            return '';
        }
    }

    /**
     * Load quagga2 library dynamically
     */
    async loadQuagga() {
        if (this.isQuaggaLoaded || window.Quagga) {
            this.isQuaggaLoaded = true;
            return;
        }

        if (this.loadQuaggaPromise) {
            return this.loadQuaggaPromise;
        }

        this.loadQuaggaPromise = new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/@ericblade/quagga2@1.8.4/dist/quagga.min.js';
            script.onload = () => {
                this.isQuaggaLoaded = true;
                resolve();
            };
            script.onerror = () => {
                reject(new Error('Failed to load quagga2 library'));
            };
            document.head.appendChild(script);
        });

        return this.loadQuaggaPromise;
    }

    /**
     * Initialize camera for barcode scanning using quagga2
     */
    async initCamera(container) {
        try {
            await this.loadQuagga();
            
            // Always create a new scanner container to avoid DOM hierarchy issues
            this.container = document.createElement('div');
            this.container.style.width = '100%';
            this.container.style.height = '300px';
            this.container.style.position = 'relative';
            this.container.style.overflow = 'hidden';
            this.container.style.border = '1px solid #ddd';
            this.container.style.borderRadius = '4px';
            
            // Add CSS styles that will apply to video and canvas elements immediately
            const style = document.createElement('style');
            style.textContent = `
                #${this.container.id || 'scanner-container'} video,
                #${this.container.id || 'scanner-container'} canvas {
                    width: 100% !important;
                    height: 100% !important;
                    object-fit: cover !important;
                    display: block !important;
                }
            `;
            
            // Give container a unique ID if it doesn't have one
            if (!this.container.id) {
                this.container.id = 'scanner-container-' + Date.now();
            }
            
            // Update the style to use the actual ID
            style.textContent = `
                #${this.container.id} video,
                #${this.container.id} canvas {
                    width: 100% !important;
                    height: 100% !important;
                    object-fit: cover !important;
                    display: block !important;
                }
            `;
            
            // Add the style to the document head
            document.head.appendChild(style);
            
            // Store style reference for cleanup
            this.containerStyle = style;
            
            // If a parent container was provided, we'll return the scanner container
            // to be appended to it, otherwise return the scanner container directly
            return this.container;
        } catch (error) {
            console.error('Error initializing camera:', error);
            throw new Error('Unable to initialize barcode scanner. Please ensure camera permissions are granted.');
        }
    }

    /**
     * Check torch capabilities after Quagga initialization
     */
    checkTorchCapabilities() {
        try {
            const track = window.Quagga.CameraAccess.getActiveTrack();
            if (track && typeof track.getCapabilities === 'function') {
                const capabilities = track.getCapabilities();
                this.torchSupported = !!capabilities.torch;
                
                // Also check current torch state to ensure consistency
                if (this.torchSupported && typeof track.getSettings === 'function') {
                    const settings = track.getSettings();
                    if (settings.torch !== undefined) {
                        this.torchEnabled = !!settings.torch;
                    }
                }
                
                return this.torchSupported;
            }
        } catch (error) {
            console.warn('Could not check torch capabilities:', error);
        }
        this.torchSupported = false;
        this.torchEnabled = false;
        return false;
    }

    /**
     * Toggle torch on/off
     */
    async toggleTorch() {
        if (!this.torchSupported) {
            throw new Error('Torch not supported on this device');
        }

        try {
            const track = window.Quagga.CameraAccess.getActiveTrack();
            if (track && typeof track.applyConstraints === 'function') {
                this.torchEnabled = !this.torchEnabled;
                await track.applyConstraints({
                    advanced: [{ torch: this.torchEnabled }]
                });
                return this.torchEnabled;
            }
        } catch (error) {
            console.error('Error toggling torch:', error);
            throw new Error('Failed to toggle torch');
        }
    }

    /**
     * Start scanning for barcodes using quagga2
     */
    async startScanning(onResult) {
        if (this.isScanning) return;
        
        try {
            await this.loadQuagga();
            
            this.isScanning = true;
            this.onResult = onResult;
            
            return new Promise((resolve, reject) => {
                // Configure quagga2
                const config = {
                    inputStream: {
                        name: "Live",
                        type: "LiveStream",
                        target: this.container,
                        constraints: {
                            width: { min: 640, ideal: 1280, max: 1920 },
                            height: { min: 480, ideal: 720, max: 1080 },
                            facingMode: "environment", // Use back camera on mobile
                            aspectRatio: { min: 1, max: 2 }
                        }
                    },
                    locator: {
                        patchSize: "medium",
                        halfSample: true
                    },
                    numOfWorkers: 2,
                    frequency: 10, // Scan frequency
                    decoder: {
                        readers: [
                            'code_128_reader', 
                            'ean_reader', 
                            'ean_8_reader',
                            'code_39_reader',
                            'code_39_vin_reader',
                            'codabar_reader',
                            'upc_reader',
                            'upc_e_reader',
                            'i2of5_reader',
                            '2of5_reader',
                            'code_93_reader'
                        ]
                    },
                    locate: true
                };

                // Initialize quagga2
                window.Quagga.init(config, (err) => {
                    if (err) {
                        console.error('Quagga initialization error:', err);
                        this.isScanning = false;
                        reject(new Error('Failed to initialize barcode scanner'));
                        return;
                    }
                    
                    // Start scanning
                    window.Quagga.start();
                    
                    // Check torch capabilities after initialization with a small delay
                    setTimeout(() => {
                        this.checkTorchCapabilities();
                    }, 500);
                    
                    // Attach detection event listener
                    window.Quagga.onDetected((result) => {
                        if (this.onResult && result.codeResult) {
                            this.onResult(result.codeResult.code);
                        }
                    });
                    
                    resolve();
                });
            });
            
        } catch (error) {
            this.isScanning = false;
            console.error('Error starting scanner:', error);
            throw error;
        }
    }

    /**
     * Stop scanning and cleanup
     */
    stopScanning() {
        this.isScanning = false;
        
        try {
            // Turn off torch before stopping if it's enabled
            if (this.torchEnabled && this.torchSupported && window.Quagga) {
                const track = window.Quagga.CameraAccess.getActiveTrack();
                if (track && typeof track.applyConstraints === 'function') {
                    track.applyConstraints({
                        advanced: [{ torch: false }]
                    }).catch(error => {
                        console.warn('Error turning off torch during cleanup:', error);
                    });
                }
            }
            
            if (window.Quagga) {
                // Remove detection event listeners
                window.Quagga.offDetected();
                window.Quagga.offProcessed();
                
                // Stop quagga2
                window.Quagga.stop();
            }
            
            // Clean up container
            if (this.container) {
                // Stop any media streams in the container
                const video = this.container.querySelector('video');
                if (video && video.srcObject) {
                    const tracks = video.srcObject.getTracks();
                    tracks.forEach(track => track.stop());
                    video.srcObject = null;
                }
                
                // Clear container content
                this.container.innerHTML = '';
                this.container = null;
            }
            
            // Clean up injected styles
            if (this.containerStyle && this.containerStyle.parentNode) {
                this.containerStyle.parentNode.removeChild(this.containerStyle);
                this.containerStyle = null;
            }
        } catch (error) {
            console.error('Error stopping scanner:', error);
        } finally {
            // Reset torch state after cleanup
            this.torchEnabled = false;
            this.torchSupported = false;
        }
    }


}

/**
 * Create barcode scanner button and modal for GTIN input fields
 */
function createBarcodeScannerButton(gtinInput) {
    if (!gtinInput || gtinInput.hasAttribute('data-barcode-scanner-added')) {
        return;
    }

    // Mark input as having scanner added immediately to prevent race conditions
    gtinInput.setAttribute('data-barcode-scanner-added', 'true');

    // Additional safety check: ensure the input is still in the DOM
    if (!document.contains(gtinInput)) {
        return;
    }

    // Create scanner button
    const scanButton = document.createElement('button');
    scanButton.type = 'button';
    scanButton.className = 'btn btn-outline-primary btn-sm ml-2';
    scanButton.innerHTML = '<i class="material-icons">qr_code_scanner</i> Scan';
    scanButton.title = 'Scan barcode with camera';

    // Insert button after the input
    const parentGroup = gtinInput.closest('.form-group') || gtinInput.closest('.mb-3') || gtinInput.parentNode;
    if (parentGroup) {
        // Create container for input and button
        const inputContainer = document.createElement('div');
        inputContainer.className = 'd-flex align-items-center';
        
        // Store reference to the parent before manipulation
        const originalParent = gtinInput.parentNode;
        const nextSibling = gtinInput.nextSibling;
        
        // Remove input from DOM temporarily to avoid ancestry issues
        originalParent.removeChild(gtinInput);
        
        // Set up the container structure
        inputContainer.appendChild(gtinInput);
        inputContainer.appendChild(scanButton);
        
        // Insert the container in the original position
        if (nextSibling) {
            originalParent.insertBefore(inputContainer, nextSibling);
        } else {
            originalParent.appendChild(inputContainer);
        }
        
        // Adjust input width
        gtinInput.style.flex = '1';
    }

    // Create scanner modal
    const modalId = 'barcodeScannerModal_' + Date.now();
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = modalId;
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Scan Barcode</h5>
                    <button type="button" class="close" data-dismiss="modal">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div class="modal-body">
                    <div id="${modalId}_camera" class="text-center" style="min-height: 300px; max-height: 400px; overflow: hidden; border: 1px solid #ddd; border-radius: 4px;">
                        <div class="mb-3">
                            <div class="spinner-border" role="status">
                                <span class="sr-only">Loading scanner...</span>
                            </div>
                            <p class="mt-2">Initializing camera and scanner...</p>
                        </div>
                    </div>
                    <div id="${modalId}_error" class="alert alert-danger d-none"></div>
                </div>
                <div class="modal-footer">
                    <button type="button" id="${modalId}_torch" class="btn btn-outline-warning d-none" style="margin-right: auto;">
                        <i class="material-icons">flashlight_off</i> <span>Torch</span>
                    </button>
                    <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);

    const scanner = new BarcodeScanner();
    
    // Handle scan button click
    scanButton.addEventListener('click', async () => {
        // Reset modal state before showing
        const cameraDiv = document.getElementById(`${modalId}_camera`);
        const errorDiv = document.getElementById(`${modalId}_error`);
        
        // Reset camera div to loading state
        cameraDiv.innerHTML = `
            <div class="mb-3">
                <div class="spinner-border" role="status">
                    <span class="sr-only">Loading scanner...</span>
                </div>
                <p class="mt-2">Initializing camera and scanner...</p>
            </div>
        `;
        
        // Hide error and clear manual input
        errorDiv.classList.add('d-none');
        errorDiv.textContent = '';
        
        $('#' + modalId).modal('show');
        
        try {
            const container = await scanner.initCamera(cameraDiv);
            
            // Clear loading message and set up container
            cameraDiv.innerHTML = '<p class="mb-2">Point camera at barcode</p>';
            
            // Safety check: only append if container is not the same as cameraDiv
            if (container && container !== cameraDiv && !cameraDiv.contains(container)) {
                // Ensure container fits within the modal
                container.style.maxWidth = '100%';
                container.style.maxHeight = '300px';
                cameraDiv.appendChild(container);
            }
            
            await scanner.startScanning((result) => {
                scanner.stopScanning();
                $('#' + modalId).modal('hide');
                handleBarcodeResult(gtinInput, result);
            });
            
            // Wait a bit longer for torch capabilities to be checked
            setTimeout(() => {
                // Show torch button if supported
                const torchButton = document.getElementById(`${modalId}_torch`);
                if (scanner.torchSupported && torchButton) {
                    torchButton.classList.remove('d-none');
                    
                    // Remove any existing event listeners first
                    const newTorchButton = torchButton.cloneNode(true);
                    torchButton.parentNode.replaceChild(newTorchButton, torchButton);
                    
                    // Update button state to reflect current torch state
                    const icon = newTorchButton.querySelector('i');
                    const text = newTorchButton.querySelector('span');
                    
                    if (scanner.torchEnabled) {
                        icon.textContent = 'flashlight_on';
                        text.textContent = 'Torch On';
                        newTorchButton.classList.remove('btn-outline-warning');
                        newTorchButton.classList.add('btn-warning');
                    } else {
                        icon.textContent = 'flashlight_off';
                        text.textContent = 'Torch';
                        newTorchButton.classList.remove('btn-warning');
                        newTorchButton.classList.add('btn-outline-warning');
                    }
                    
                    // Add fresh torch toggle event listener
                    newTorchButton.addEventListener('click', async () => {
                        try {
                            const isEnabled = await scanner.toggleTorch();
                            
                            if (isEnabled) {
                                icon.textContent = 'flashlight_on';
                                text.textContent = 'Torch On';
                                newTorchButton.classList.remove('btn-outline-warning');
                                newTorchButton.classList.add('btn-warning');
                            } else {
                                icon.textContent = 'flashlight_off';
                                text.textContent = 'Torch';
                                newTorchButton.classList.remove('btn-warning');
                                newTorchButton.classList.add('btn-outline-warning');
                            }
                        } catch (error) {
                            console.error('Error toggling torch:', error);
                            // Could show a toast message here if needed
                        }
                    });
                }
            }, 1000);
            
        } catch (error) {
            errorDiv.textContent = error.message;
            errorDiv.classList.remove('d-none');
            
            // Hide loading spinner on error
            cameraDiv.innerHTML = '<p class="text-muted">Camera initialization failed. Please use manual entry below.</p>';
        }
    });

    // Cleanup when modal is hidden
    $('#' + modalId).on('hidden.bs.modal', () => {
        scanner.stopScanning();
        
        // Reset modal state for next use
        const cameraDiv = document.getElementById(`${modalId}_camera`);
        const errorDiv = document.getElementById(`${modalId}_error`);
        const torchButton = document.getElementById(`${modalId}_torch`);
        
        // Reset to initial loading state
        cameraDiv.innerHTML = `
            <div class="mb-3">
                <div class="spinner-border" role="status">
                    <span class="sr-only">Loading scanner...</span>
                </div>
                <p class="mt-2">Initializing camera and scanner...</p>
            </div>
        `;
        
        // Clear error and manual input
        errorDiv.classList.add('d-none');
        errorDiv.textContent = '';
        
        // Hide and reset torch button
        if (torchButton) {
            torchButton.classList.add('d-none');
            torchButton.classList.remove('btn-warning');
            torchButton.classList.add('btn-outline-warning');
            const icon = torchButton.querySelector('i');
            const text = torchButton.querySelector('span');
            if (icon) icon.textContent = 'flashlight_off';
            if (text) text.textContent = 'Torch';
        }
    });
    
    // Also cleanup when modal is about to be shown (double safety)
    $('#' + modalId).on('show.bs.modal', () => {
        // Ensure any previous scanner instance is stopped
        scanner.stopScanning();
        
        // Hide torch button initially (but don't reset scanner state yet)
        const torchButton = document.getElementById(`${modalId}_torch`);
        if (torchButton) {
            torchButton.classList.add('d-none');
            torchButton.classList.remove('btn-warning');
            torchButton.classList.add('btn-outline-warning');
            const icon = torchButton.querySelector('i');
            const text = torchButton.querySelector('span');
            if (icon) icon.textContent = 'flashlight_off';
            if (text) text.textContent = 'Torch';
        }
    });
}

/**
 * Handle barcode scan result by parsing GS1 data and populating form fields
 */
function handleBarcodeResult(gtinInput, barcodeData) {
    const parsed = BarcodeScanner.parseGS1(barcodeData);
    
    // Set GTIN value
    gtinInput.value = parsed.gtin;
    gtinInput.dispatchEvent(new Event('input', { bubbles: true }));
    
    // Try to populate lot and expiration fields if they exist
    const form = gtinInput.closest('form');
    if (form) {
        // Look for lot/batch number field
        const lotFields = ['lot_number', 'lot', 'batch', 'batch_number'];
        for (const fieldName of lotFields) {
            const lotInput = form.querySelector(`[name="${fieldName}"], #id_${fieldName}`);
            if (lotInput && parsed.lot) {
                lotInput.value = parsed.lot;
                lotInput.dispatchEvent(new Event('input', { bubbles: true }));
                break;
            }
        }
        
        // Look for expiration date field
        const expirationFields = ['expiration_date', 'expiry_date', 'expires', 'expiration'];
        for (const fieldName of expirationFields) {
            const expirationInput = form.querySelector(`[name="${fieldName}"], #id_${fieldName}`);
            if (expirationInput && parsed.expiration) {
                expirationInput.value = parsed.expiration;
                expirationInput.dispatchEvent(new Event('input', { bubbles: true }));
                break;
            }
        }
    }
    
    // Show success message
    showParseResult(gtinInput, parsed);
}

/**
 * Show parse result as a temporary message
 */
function showParseResult(gtinInput, parsed) {
    const parts = [];
    if (parsed.gtin) parts.push(`GTIN: ${parsed.gtin}`);
    if (parsed.lot) parts.push(`Lot: ${parsed.lot}`);
    if (parsed.expiration) parts.push(`Expires: ${parsed.expiration}`);
    
    if (parts.length > 1) {
        const message = document.createElement('div');
        message.className = 'alert alert-success alert-dismissible fade show mt-2';
        message.innerHTML = `
            <strong>Parsed GS1 data:</strong> ${parts.join(', ')}
            <button type="button" class="close" data-dismiss="alert">
                <span aria-hidden="true">&times;</span>
            </button>
        `;
        
        const container = gtinInput.closest('.form-group') || gtinInput.closest('.mb-3') || gtinInput.parentNode;
        
        // Safety check: ensure container exists and message is not already in DOM
        if (container && !message.parentNode) {
            container.appendChild(message);
        }
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (message.parentNode) {
                message.remove();
            }
        }, 5000);
    }
}

/**
 * Add GS1 parsing to GTIN input on blur
 */
function addGS1ParseToInput(gtinInput) {
    if (!gtinInput || gtinInput.hasAttribute('data-gs1-parser-added')) {
        return;
    }

    // Mark input as having parser added immediately to prevent race conditions
    gtinInput.setAttribute('data-gs1-parser-added', 'true');
    
    // Additional safety check: ensure the input is still in the DOM
    if (!document.contains(gtinInput)) {
        return;
    }
    
    gtinInput.addEventListener('blur', function() {
        const value = this.value.trim();
        if (!value) return;
        
        const parsed = BarcodeScanner.parseGS1(value);
        
        // Always update GTIN field with the parsed GTIN value
        if (parsed.gtin && parsed.gtin !== value) {
            this.value = parsed.gtin;
            this.dispatchEvent(new Event('input', { bubbles: true }));
        }
        
        // Try to populate other fields if they exist
        const form = this.closest('form');
        if (form) {
            // Populate lot field
            if (parsed.lot) {
                const lotFields = ['lot_number', 'lot', 'batch', 'batch_number'];
                for (const fieldName of lotFields) {
                    const lotInput = form.querySelector(`[name="${fieldName}"], #id_${fieldName}`);
                    if (lotInput && !lotInput.value) {
                        lotInput.value = parsed.lot;
                        lotInput.dispatchEvent(new Event('input', { bubbles: true }));
                        break;
                    }
                }
            }
            
            // Populate expiration field
            if (parsed.expiration) {
                const expirationFields = ['expiration_date', 'expiry_date', 'expires', 'expiration'];
                for (const fieldName of expirationFields) {
                    const expirationInput = form.querySelector(`[name="${fieldName}"], #id_${fieldName}`);
                    if (expirationInput && !expirationInput.value) {
                        expirationInput.value = parsed.expiration;
                        expirationInput.dispatchEvent(new Event('input', { bubbles: true }));
                        break;
                    }
                }
            }
        }
        
        // Show parse result if additional data was found
        if (parsed.lot || parsed.expiration) {
            showParseResult(this, parsed);
        }
    });
}

/**
 * Initialize barcode scanner for all GTIN inputs on the page
 */
function initBarcodeScanner() {
    // Find all GTIN input fields (including dynamically added ones)
    const gtinInputs = document.querySelectorAll('input[id="id_gtin"]');
    
    gtinInputs.forEach(input => {
        addGS1ParseToInput(input);
        
        // Add scanner button if device has camera support and is likely a mobile device
        // Quagga2 works better on devices with good camera support
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            createBarcodeScannerButton(input);
        }
    });
    
    // Also watch for dynamically added GTIN inputs
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) { // Element node
                    const newGtinInputs = node.querySelectorAll ? 
                        node.querySelectorAll('input[id="id_gtin"]') : 
                        [];
                    
                    newGtinInputs.forEach(input => {
                        addGS1ParseToInput(input);
                        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                            createBarcodeScannerButton(input);
                        }
                    });
                    
                    // Check if the added node itself is a GTIN input
                    if (node.matches && node.matches('input[id="id_gtin"]')) {
                        addGS1ParseToInput(node);
                        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                            createBarcodeScannerButton(node);
                        }
                    }
                }
            });
        });
    });
    
    // Start observing
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

// Auto-initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBarcodeScanner);
} else {
    initBarcodeScanner();
}

// Export for manual initialization
window.BarcodeScanner = BarcodeScanner;
window.initBarcodeScanner = initBarcodeScanner;