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
            script.src = 'https://cdn.jsdelivr.net/npm/@ericblade/quagga2@1.8.6/dist/quagga.min.js';
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
            
            this.container = container;
            
            // Create scanner container if not provided
            if (!this.container) {
                this.container = document.createElement('div');
                this.container.style.width = '100%';
                this.container.style.height = '300px';
                this.container.style.position = 'relative';
            }

            return this.container;
        } catch (error) {
            console.error('Error initializing camera:', error);
            throw new Error('Unable to initialize barcode scanner. Please ensure camera permissions are granted.');
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
            if (window.Quagga) {
                // Remove detection event listeners
                window.Quagga.offDetected();
                window.Quagga.offProcessed();
                
                // Stop quagga2
                window.Quagga.stop();
            }
        } catch (error) {
            console.error('Error stopping scanner:', error);
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

    // Mark input as having scanner added
    gtinInput.setAttribute('data-barcode-scanner-added', 'true');

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
        
        // Move input into container
        gtinInput.parentNode.insertBefore(inputContainer, gtinInput);
        inputContainer.appendChild(gtinInput);
        inputContainer.appendChild(scanButton);
        
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
                    <div id="${modalId}_camera" class="text-center" style="min-height: 300px;">
                        <div class="mb-3">
                            <div class="spinner-border" role="status">
                                <span class="sr-only">Loading scanner...</span>
                            </div>
                            <p class="mt-2">Initializing camera and scanner...</p>
                        </div>
                    </div>
                    <div id="${modalId}_error" class="alert alert-danger d-none"></div>
                    <div class="mt-3">
                        <label for="${modalId}_manual" class="form-label">Or enter barcode manually:</label>
                        <input type="text" class="form-control" id="${modalId}_manual" placeholder="Enter barcode...">
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="${modalId}_use">Use Manual Entry</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);

    const scanner = new BarcodeScanner();
    
    // Handle scan button click
    scanButton.addEventListener('click', async () => {
        $('#' + modalId).modal('show');
        
        try {
            const cameraDiv = document.getElementById(`${modalId}_camera`);
            const container = await scanner.initCamera(cameraDiv);
            
            // Clear loading message and set up container
            cameraDiv.innerHTML = '<p class="mb-2">Point camera at barcode</p>';
            cameraDiv.appendChild(container);
            
            await scanner.startScanning((result) => {
                scanner.stopScanning();
                $('#' + modalId).modal('hide');
                handleBarcodeResult(gtinInput, result);
            });
            
        } catch (error) {
            const errorDiv = document.getElementById(`${modalId}_error`);
            errorDiv.textContent = error.message;
            errorDiv.classList.remove('d-none');
            
            // Hide loading spinner on error
            const cameraDiv = document.getElementById(`${modalId}_camera`);
            cameraDiv.innerHTML = '<p class="text-muted">Camera initialization failed. Please use manual entry below.</p>';
        }
    });

    // Handle manual entry
    document.getElementById(`${modalId}_use`).addEventListener('click', () => {
        const manualInput = document.getElementById(`${modalId}_manual`);
        if (manualInput.value.trim()) {
            $('#' + modalId).modal('hide');
            handleBarcodeResult(gtinInput, manualInput.value.trim());
        }
    });

    // Cleanup when modal is hidden
    $('#' + modalId).on('hidden.bs.modal', () => {
        scanner.stopScanning();
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
        container.appendChild(message);
        
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

    gtinInput.setAttribute('data-gs1-parser-added', 'true');
    
    gtinInput.addEventListener('blur', function() {
        const value = this.value.trim();
        if (!value) return;
        
        const parsed = BarcodeScanner.parseGS1(value);
        
        // If parsing extracted additional data, update the form
        if (parsed.lot || parsed.expiration) {
            // Update GTIN field with just the GTIN part
            if (parsed.gtin && parsed.gtin !== value) {
                this.value = parsed.gtin;
            }
            
            // Try to populate other fields
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
            
            // Show parse result
            showParseResult(this, parsed);
        }
    });
}

/**
 * Initialize barcode scanner for all GTIN inputs on the page
 */
function initBarcodeScanner() {
    // Find all GTIN input fields (including dynamically added ones)
    const gtinInputs = document.querySelectorAll('input[name="gtin"], input[id*="gtin"], input[id*="GTIN"], input[id="id_gtin"]');
    
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
                        node.querySelectorAll('input[name="gtin"], input[id*="gtin"], input[id*="GTIN"], input[id="id_gtin"]') : 
                        [];
                    
                    newGtinInputs.forEach(input => {
                        addGS1ParseToInput(input);
                        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                            createBarcodeScannerButton(input);
                        }
                    });
                    
                    // Check if the added node itself is a GTIN input
                    if (node.matches && node.matches('input[name="gtin"], input[id*="gtin"], input[id*="GTIN"], input[id="id_gtin"]')) {
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