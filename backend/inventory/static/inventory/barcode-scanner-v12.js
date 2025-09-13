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

    

    static parseGS1(data) {
        const result = {};
        let remainingData = data;
        const separator = String.fromCharCode(29);

        // Define a map of relevant AIs for your specific output keys
        const ais = {
            "01": { key: "gtin", isVariableLength: false, length: 14 },
            "10": { key: "lot", isVariableLength: true, length: 20 },
            "17": { key: "expiration", isVariableLength: false, length: 6 },
            "21": { key: "serial", isVariableLength: true, length: 20 },
            "11": { key: "production_date", isVariableLength: false, length: 6 },
            "240": { key: "additional_id", isVariableLength: true, length: 30 },
            "91": { key: "company_internal", isVariableLength: true, length: 30 },
        };

        const fixedLengthAis = {};
        for (let ai in ais) {
            if (!ais[ai].isVariableLength) {
                fixedLengthAis[ai] = ais[ai].length;
            }
        }

        while (remainingData.length > 0) {
            let aiCode = "";
            let dataField = "";
            
            // Check for AIs with parentheses first
            const parenthesisMatch = remainingData.match(/^\((\d{2,4})\)/);
            
            if (parenthesisMatch) {
                aiCode = parenthesisMatch[1];
                remainingData = remainingData.substring(parenthesisMatch[0] .length);
            } else {
                // If no parentheses, try to find the AI at the start of the string
                let potentialAi;
                if (remainingData.length >= 4) {
                    potentialAi = remainingData.substring(0, 4);
                    if (ais[potentialAi]) aiCode = potentialAi;
                }
                if (!aiCode && remainingData.length >= 3) {
                    potentialAi = remainingData.substring(0, 3);
                    if (ais[potentialAi]) aiCode = potentialAi;
                }
                if (!aiCode && remainingData.length >= 2) {
                    potentialAi = remainingData.substring(0, 2);
                    if (ais[potentialAi]) aiCode = potentialAi;
                }

                if (aiCode) {
                    remainingData = remainingData.substring(aiCode.length);
                }
            }
            
            if (!aiCode || !ais[aiCode]) {
                // If an unknown or irrelevant AI is found, we need to skip it to continue parsing
                // For fixed-length AIs we need to know the length to skip ahead
                // This is a simplified approach for demonstration
                console.warn(`Unknown or irrelevant AI code "${aiCode}" detected. Skipping to next possible AI.`);
                
                // Find the next potential AI to resume parsing
                let nextAiIndex = -1;
                for(let key in ais){
                    const index = remainingData.indexOf(key);
                    if(index !== -1 && (nextAiIndex === -1 || index < nextAiIndex)){
                        nextAiIndex = index;
                    }
                }
                
                if(nextAiIndex !== -1){
                    remainingData = remainingData.substring(nextAiIndex);
                } else {
                    remainingData = ""; // No more AIs to parse, so we can stop
                }
                continue; // Go to the next loop iteration
            }

            let aiInfo = ais[aiCode];
            
            if (fixedLengthAis[aiCode]) {
                let dataLength = fixedLengthAis[aiCode];
                dataField = remainingData.substring(0, dataLength);
                remainingData = remainingData.substring(dataLength);
            } else {
                // For variable-length fields, look for separator, next parenthesis, or end of string
                const separatorIndex = remainingData.indexOf(separator);
                const nextParenthesisIndex = remainingData.indexOf('(');
                
                let endIndex = remainingData.length; // Default to end of string
                
                // Find the earliest valid delimiter
                if (separatorIndex !== -1 && (nextParenthesisIndex === -1 || separatorIndex < nextParenthesisIndex)) {
                    endIndex = separatorIndex;
                    dataField = remainingData.substring(0, endIndex);
                    remainingData = remainingData.substring(endIndex + 1); // Skip separator
                } else if (nextParenthesisIndex !== -1) {
                    endIndex = nextParenthesisIndex;
                    dataField = remainingData.substring(0, endIndex);
                    remainingData = remainingData.substring(endIndex); // Don't skip parenthesis
                } else {
                    dataField = remainingData;
                    remainingData = "";
                }
            }
            
            if (dataField) {
                result[aiInfo.key] = dataField;
            }
        }
        
        return result;
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
    showParseResult(gtinInput, barcodeData, parsed);
}

/**
 * Show parse result as a temporary message
 */
function showParseResult(gtinInput, barcodeData, parsed) {
    const parts = [];

    if (!parsed) return;

    if (parsed.gtin) parts.push(`<strong>GTIN:</strong> ${parsed.gtin}`);
    if (parsed.lot) parts.push(`<strong>Lot:</strong> ${parsed.lot}`);
    if (parsed.expiration) parts.push(`<strong>Expires:</strong> ${parsed.expiration}`);

    if (parts.length >= 1) {
        const message = document.createElement('div');
        message.className = 'alert alert-success alert-dismissible fade show mt-2';
        message.innerHTML = `
            <strong>Parsed GS1 data:</strong> ${barcodeData} 
            <br/> ${parts.join(', ')}
            <button type="button" class="close" data-dismiss="alert">
                <span aria-hidden="true">&times;</span>
            </button>
        `;
        
        const container = gtinInput.closest('.form-group') || gtinInput.closest('.mb-3') || gtinInput.parentNode;
        
        // Safety check: ensure container exists
        if (container && !message.parentNode) {
            // Remove any existing parse result messages first
            const existingMessages = container.querySelectorAll('.alert-success');
            existingMessages.forEach(existing => {
                if (existing.innerHTML.includes('Parsed GS1 data:')) {
                    existing.remove();
                }
            });
            
            container.appendChild(message);
        }
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
        if (!parsed) return; // Only proceed if parsing was successful

        // Always clear field / set GTIN if parsed successfully
        this.value = parsed.gtin || "";
        gtinInput.dispatchEvent(new Event('input', { bubbles: true }));


        
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
        if (parsed.lot || parsed.expiration || parsed.gtin) {
            showParseResult(this, value, parsed);
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