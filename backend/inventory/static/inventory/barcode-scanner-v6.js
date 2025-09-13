/**
 * Barcode Scanner and GS1 Parser Module
 * Provides functionality for parsing GS1 Application Identifiers and camera-based barcode scanning
 * Uses ZXing-JS library for comprehensive barcode detection including Data Matrix (GS1)
 */

class BarcodeScanner {
    constructor() {
        this.container = null;
        this.isScanning = false;
        this.onResult = null;
        this.isZXingLoaded = false;
        this.loadZXingPromise = null;
        this.torchSupported = false;
        this.torchEnabled = false;
        this.codeReader = null;
        this.stream = null;
        this.videoElement = null;
        this.selectedDeviceId = null;
    }

    /**
     * Parse GS1 Application Identifiers from a barcode string
     * Supports both parentheses format: (01)GTIN(10)LOT(17)YYMMDD
     * and FNC1 format: 01GTIN<FNC1>10LOT<FNC1>17YYMMDD
     * FNC1 is typically ASCII character 29 (Group Separator)
     */
    static parseGS1(barcodeData) {
        if (!barcodeData || typeof barcodeData !== 'string') {
            return { gtin: barcodeData || '', lot: '', expiration: '' };
        }

        // Remove any whitespace
        const data = barcodeData.trim();
        
        // First try parentheses format: (01)GTIN(10)LOT(17)YYMMDD
        const parenthesesPattern = /\((\d{2,4})\)([^(]*)/g;
        const parenthesesMatches = [...data.matchAll(parenthesesPattern)];
        
        if (parenthesesMatches.length > 0) {
            return this._parseGS1Matches(parenthesesMatches);
        }
        
        // Try FNC1 format (ASCII 29 - Group Separator)
        // FNC1 can be represented as \u001D (ASCII 29), \x1D, or sometimes as ]C1
        const fnc1Chars = ['\u001D', '\x1D', String.fromCharCode(29)];
        let fnc1Data = data;
        let fnc1Char = null;
        
        // Find which FNC1 character is used
        for (const char of fnc1Chars) {
            if (data.includes(char)) {
                fnc1Char = char;
                break;
            }
        }
        
        // Also check for common text representations of FNC1
        if (!fnc1Char) {
            if (data.includes(']C1')) {
                fnc1Data = data.replace(/\]C1/g, '\u001D');
                fnc1Char = '\u001D';
            } else if (data.includes('<FNC1>')) {
                fnc1Data = data.replace(/<FNC1>/g, '\u001D');
                fnc1Char = '\u001D';
            } else if (data.includes('[FNC1]')) {
                fnc1Data = data.replace(/\[FNC1\]/g, '\u001D');
                fnc1Char = '\u001D';
            }
        }
        
        if (fnc1Char) {
            return this._parseGS1FNC1Format(fnc1Data, fnc1Char);
        }
        
        // No GS1 identifiers found, treat as plain GTIN
        return { gtin: data, lot: '', expiration: '' };
    }

    /**
     * Parse GS1 data in FNC1 format
     */
    static _parseGS1FNC1Format(data, fnc1Char) {
        const result = { gtin: '', lot: '', expiration: '' };
        
        // Split by FNC1 character
        const segments = data.split(fnc1Char);
        
        // Parse each segment
        for (let segment of segments) {
            segment = segment.trim();
            if (!segment) continue;
            
            // Extract Application Identifier and data
            const aiMatch = this._extractApplicationIdentifier(segment);
            if (aiMatch) {
                const { ai, value } = aiMatch;
                
                switch (ai) {
                    case '01':  // GTIN (14 digits)
                        result.gtin = value;
                        break;
                    case '10':  // Lot/Batch Number (variable length, up to 20 alphanumeric)
                        result.lot = value;
                        break;
                    case '17':  // Expiration Date (6 digits YYMMDD)
                        result.expiration = this.parseGS1Date(value);
                        break;
                }
            }
        }
        
        return result;
    }

    /**
     * Extract Application Identifier and its value from a segment
     * Uses GS1 Application Identifier length rules
     */
    static _extractApplicationIdentifier(segment) {
        if (!segment || segment.length < 3) return null;
        
        // Common Application Identifiers and their data lengths
        const aiLengths = {
            '00': 18,   // SSCC (fixed length)
            '01': 14,   // GTIN (fixed length) 
            '02': 14,   // GTIN of trade items contained in a logistic unit
            '10': -1,   // Batch/lot number (variable length)
            '11': 6,    // Production date (YYMMDD)
            '12': 6,    // Due date (YYMMDD)
            '13': 6,    // Packaging date (YYMMDD)
            '15': 6,    // Best before date (YYMMDD)
            '16': 6,    // Sell by date (YYMMDD)
            '17': 6,    // Expiration date (YYMMDD)
            '20': 2,    // Internal product variant
            '21': -1,   // Serial number (variable length)
            '22': -1,   // Consumer product variant (variable length)
            '240': -1,  // Additional product identification assigned by the manufacturer (variable length)
            '241': -1,  // Customer part number (variable length)
            '242': -1,  // Made-to-Order variation number (variable length)
            '243': -1,  // Packaging component number (variable length)
            '250': -1,  // Secondary serial number (variable length)
            '251': -1,  // Reference to source entity (variable length)
            '253': -1,  // Global Document Type Identifier (variable length)
            '254': -1,  // GLN extension component (variable length)
            '30': -1,   // Variable count (variable length)
            '310': 6,   // Net weight, kilograms
            '311': 6,   // Length or first dimension, metres
            '312': 6,   // Width, diameter, or second dimension, metres
            '313': 6,   // Depth, thickness, height, or third dimension, metres
            '314': 6,   // Area, square metres
            '315': 6,   // Net volume, litres
            '316': 6,   // Net volume, cubic metres
            '320': 6,   // Net weight, pounds
            '321': 6,   // Length or first dimension, inches
            '322': 6,   // Length or first dimension, feet
            '323': 6,   // Length or first dimension, yards
            '324': 6,   // Width, diameter, or second dimension, inches
            '325': 6,   // Width, diameter, or second dimension, feet
            '326': 6,   // Width, diameter, or second dimension, yards
            '327': 6,   // Depth, thickness, height, or third dimension, inches
            '328': 6,   // Depth, thickness, height, or third dimension, feet
            '329': 6,   // Depth, thickness, height, or third dimension, yards
            '330': 6,   // Logistic weight, kilograms
            '331': 6,   // Length or first dimension, metres
            '332': 6,   // Width, diameter, or second dimension, metres
            '333': 6,   // Depth, thickness, height, or third dimension, metres
            '334': 6,   // Area, square metres
            '335': 6,   // Logistic volume, litres
            '336': 6,   // Logistic volume, cubic metres
            '340': 6,   // Logistic weight, pounds
            '341': 6,   // Length or first dimension, inches
            '342': 6,   // Length or first dimension, feet
            '343': 6,   // Length or first dimension, yards
            '344': 6,   // Width, diameter, or second dimension, inches
            '345': 6,   // Width, diameter, or second dimension, feet
            '346': 6,   // Width, diameter, or second dimension, yards
            '347': 6,   // Depth, thickness, height, or third dimension, inches
            '348': 6,   // Depth, thickness, height, or third dimension, feet
            '349': 6,   // Depth, thickness, height, or third dimension, yards
            '350': 6,   // Area, square inches
            '351': 6,   // Area, square feet
            '352': 6,   // Area, square yards
            '353': 6,   // Area, square inches
            '354': 6,   // Area, square feet
            '355': 6,   // Area, square yards
            '356': 6,   // Net weight, troy ounces
            '357': 6,   // Net weight or volume, ounces
            '360': 6,   // Volume, quarts
            '361': 6,   // Volume, gallons
            '362': 6,   // Logistic volume, quarts
            '363': 6,   // Logistic volume, gallons
            '364': 6,   // Net volume, cubic inches
            '365': 6,   // Net volume, cubic feet
            '366': 6,   // Net volume, cubic yards
            '367': 6,   // Logistic volume, cubic inches
            '368': 6,   // Logistic volume, cubic feet
            '369': 6,   // Logistic volume, cubic yards
            '37': -1,   // Count of trade items or trade item pieces contained in a logistic unit (variable length)
            '390': -1,  // Applicable amount payable or Coupon value, local currency (variable length)
            '391': -1,  // Applicable amount payable with ISO currency code (variable length)
            '392': -1,  // Applicable amount payable, single monetary area (variable length)
            '393': -1,  // Applicable amount payable with ISO currency code (variable length)
            '394': -1,  // Percentage discount of a coupon (variable length)
            '400': -1,  // Customer's purchase order number (variable length)
            '401': -1,  // Global Identification Number for Consignment (variable length)
            '402': 17,  // Global Shipment Identification Number (fixed length)
            '403': -1,  // Routing code (variable length)
            '410': 13,  // Ship to / Deliver to Global Location Number
            '411': 13,  // Bill to / Invoice to Global Location Number
            '412': 13,  // Purchased from Global Location Number
            '413': 13,  // Ship for / Deliver for / Forward to Global Location Number
            '414': 13,  // Identification of a physical location - Global Location Number
            '415': 13,  // Global Location Number of the invoicing party
            '416': 13,  // Global Location Number of the production or service location
            '417': 13,  // Party Global Location Number
            '420': -1,  // Ship to / Deliver to postal code within a single postal authority (variable length)
            '421': -1,  // Ship to / Deliver to postal code with ISO country code (variable length)
            '422': 3,   // Country of origin of a trade item
            '423': -1,  // Country of initial processing (variable length)
            '424': 3,   // Country of processing
            '425': 3,   // Country of disassembly
            '426': 3,   // Country covering full process chain
            '427': -1,  // Country subdivision Of origin (variable length)
            '7001': 13, // NATO Stock Number (NSN)
            '7002': -1, // UN/ECE meat carcasses and cuts classification (variable length)
            '7003': 10, // Expiration date and time
            '7004': -1, // Active potency (variable length)
            '7005': -1, // Catch area (variable length)
            '7006': 6,  // First freeze date
            '7007': -1, // Harvest date (variable length)
            '7008': -1, // Species for fishery purposes (variable length)
            '7009': -1, // Fishing gear type (variable length)
            '7010': -1, // Production method (variable length)
            '7020': -1, // Refurbishment lot ID (variable length)
            '7021': -1, // Functional status (variable length)
            '7022': -1, // Revision status (variable length)
            '7023': -1, // Global Individual Asset Identifier of an assembly (variable length)
            '8001': 14, // Roll products (width, length, core diameter, direction, splices)
            '8002': -1, // Cellular mobile telephone identifier (variable length)
            '8003': -1, // Global Returnable Asset Identifier (variable length)
            '8004': -1, // Global Individual Asset Identifier (variable length)
            '8005': 6,  // Price per unit of measure
            '8006': 18, // Identification of an individual trade item piece
            '8007': -1, // International Bank Account Number (variable length)
            '8008': -1, // Date and time of production (variable length)
            '8009': -1, // Optically Readable Sensor Indicator (variable length)
            '8010': -1, // Component/Part Identifier (variable length)
            '8011': -1, // Component/Part Identifier serial number (variable length)
            '8012': -1, // Software version (variable length)
            '8013': -1, // Global Model Number (variable length)
            '8017': 18, // Global Service Relation Number to identify the relationship between an organisation offering services and the provider of services
            '8018': 18, // Global Service Relation Number to identify the relationship between an organisation offering services and the recipient of services
            '8019': -1, // Service Relation Instance Number (variable length)
            '8020': -1, // Payment slip reference number (variable length)
            '8026': 18, // Identification of pieces of a trade item
            '8110': -1, // Coupon code identification for use in North America (variable length)
            '8111': 4,  // Loyalty points of a coupon
            '8112': -1, // Paperless coupon code identification for use in North America (variable length)
            '8200': -1, // Extended packaging URL (variable length)
            '90': -1,   // Information mutually agreed between trading partners (variable length)
            '91': -1,   // Company internal information (variable length)
            '92': -1,   // Company internal information (variable length)
            '93': -1,   // Company internal information (variable length)
            '94': -1,   // Company internal information (variable length)
            '95': -1,   // Company internal information (variable length)
            '96': -1,   // Company internal information (variable length)
            '97': -1,   // Company internal information (variable length)
            '98': -1,   // Company internal information (variable length)
            '99': -1    // Company internal information (variable length)
        };
        
        // Try different AI lengths (2, 3, 4 digits)
        for (let aiLen = 2; aiLen <= 4 && aiLen <= segment.length; aiLen++) {
            const ai = segment.substring(0, aiLen);
            const dataLength = aiLengths[ai];
            
            if (dataLength !== undefined) {
                let value;
                if (dataLength === -1) {
                    // Variable length - take remaining data
                    value = segment.substring(aiLen);
                } else {
                    // Fixed length
                    value = segment.substring(aiLen, aiLen + dataLength);
                }
                
                if (value) {
                    return { ai, value };
                }
            }
        }
        
        return null;
    }

    /**
     * Parse GS1 matches from parentheses format
     */
    static _parseGS1Matches(matches) {
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
     * Load ZXing-JS library dynamically
     */
    async loadZXing() {
        if (this.isZXingLoaded || window.ZXing) {
            this.isZXingLoaded = true;
            return;
        }

        if (this.loadZXingPromise) {
            return this.loadZXingPromise;
        }

        this.loadZXingPromise = new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://unpkg.com/@zxing/library@latest/umd/index.min.js';
            script.onload = () => {
                this.isZXingLoaded = true;
                resolve();
            };
            script.onerror = () => {
                reject(new Error('Failed to load ZXing-JS library'));
            };
            document.head.appendChild(script);
        });

        return this.loadZXingPromise;
    }

    /**
     * Initialize camera for barcode scanning using ZXing-JS
     */
    async initCamera(container) {
        try {
            await this.loadZXing();
            
            // Create video element for camera preview
            this.videoElement = document.createElement('video');
            this.videoElement.style.width = '100%';
            this.videoElement.style.height = '300px';
            this.videoElement.style.objectFit = 'cover';
            this.videoElement.style.border = '1px solid #ddd';
            this.videoElement.style.borderRadius = '4px';
            this.videoElement.autoplay = true;
            this.videoElement.muted = true;
            this.videoElement.playsInline = true;
            
            // Always create a new scanner container to avoid DOM hierarchy issues
            this.container = document.createElement('div');
            this.container.style.width = '100%';
            this.container.style.height = '300px';
            this.container.style.position = 'relative';
            this.container.style.overflow = 'hidden';
            this.container.style.border = '1px solid #ddd';
            this.container.style.borderRadius = '4px';
            
            // Add the video element to the container
            this.container.appendChild(this.videoElement);
            
            return this.container;
        } catch (error) {
            console.error('Error initializing camera:', error);
            throw new Error('Unable to initialize barcode scanner. Please ensure camera permissions are granted.');
        }
    }

    /**
     * Check torch capabilities
     */
    checkTorchCapabilities() {
        try {
            if (this.stream) {
                const videoTrack = this.stream.getVideoTracks()[0];
                if (videoTrack && typeof videoTrack.getCapabilities === 'function') {
                    const capabilities = videoTrack.getCapabilities();
                    this.torchSupported = !!capabilities.torch;
                    
                    // Also check current torch state to ensure consistency
                    if (this.torchSupported && typeof videoTrack.getSettings === 'function') {
                        const settings = videoTrack.getSettings();
                        if (settings.torch !== undefined) {
                            this.torchEnabled = !!settings.torch;
                        }
                    }
                    
                    return this.torchSupported;
                }
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
            if (this.stream) {
                const videoTrack = this.stream.getVideoTracks()[0];
                if (videoTrack && typeof videoTrack.applyConstraints === 'function') {
                    this.torchEnabled = !this.torchEnabled;
                    await videoTrack.applyConstraints({
                        advanced: [{ torch: this.torchEnabled }]
                    });
                    return this.torchEnabled;
                }
            }
        } catch (error) {
            console.error('Error toggling torch:', error);
            throw new Error('Failed to toggle torch');
        }
    }

    /**
     * Start scanning for barcodes using ZXing-JS
     */
    async startScanning(onResult) {
        if (this.isScanning) return;
        
        try {
            await this.loadZXing();
            
            this.isScanning = true;
            this.onResult = onResult;
            
            // Create a multi-format reader that supports various barcode types including Data Matrix
            const codeReader = new window.ZXing.BrowserMultiFormatReader();
            this.codeReader = codeReader;
            
            // Get video input devices using the correct API
            const videoInputDevices = await this.codeReader.getVideoInputDevices();
            
            // Prefer back camera if available
            let selectedDeviceId = undefined;
            if (videoInputDevices.length > 0) {
                // Try to find back camera
                const backCamera = videoInputDevices.find(device => 
                    device.label.toLowerCase().includes('back') || 
                    device.label.toLowerCase().includes('rear') ||
                    device.label.toLowerCase().includes('environment')
                );
                selectedDeviceId = backCamera ? backCamera.deviceId : videoInputDevices[0].deviceId;
            }
            this.selectedDeviceId = selectedDeviceId;
            
            // Start decoding from video device
            const constraints = {
                video: {
                    deviceId: selectedDeviceId ? { exact: selectedDeviceId } : undefined,
                    facingMode: selectedDeviceId ? undefined : { ideal: 'environment' },
                    width: { min: 640, ideal: 1280, max: 1920 },
                    height: { min: 480, ideal: 720, max: 1080 }
                }
            };
            
            // Get user media
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.videoElement.srcObject = this.stream;
            
            // Wait for video to load
            await new Promise((resolve) => {
                this.videoElement.onloadedmetadata = resolve;
            });
            
            // Check torch capabilities after stream is ready
            setTimeout(() => {
                this.checkTorchCapabilities();
            }, 500);
            
            // Start continuous decoding
            this.codeReader.decodeFromVideoDevice(selectedDeviceId, this.videoElement, (result, err) => {
                if (result) {
                    // Successfully decoded a barcode
                    if (this.onResult) {
                        this.onResult(result.getText());
                    }
                }
                
                if (err && !(err instanceof window.ZXing.NotFoundException)) {
                    // Only log non-"not found" errors
                    console.warn('Decode error:', err);
                }
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
            if (this.torchEnabled && this.torchSupported && this.stream) {
                const videoTrack = this.stream.getVideoTracks()[0];
                if (videoTrack && typeof videoTrack.applyConstraints === 'function') {
                    videoTrack.applyConstraints({
                        advanced: [{ torch: false }]
                    }).catch(error => {
                        console.warn('Error turning off torch during cleanup:', error);
                    });
                }
            }
            
            // Stop the code reader
            if (this.codeReader) {
                this.codeReader.reset();
                this.codeReader = null;
            }
            
            // Stop media stream
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
                this.stream = null;
            }
            
            // Clear video element
            if (this.videoElement) {
                this.videoElement.srcObject = null;
                this.videoElement = null;
            }
            
            // Clear container
            if (this.container) {
                this.container.innerHTML = '';
                this.container = null;
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