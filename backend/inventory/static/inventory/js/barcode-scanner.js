/**
 * Barcode Scanner using device camera
 * Requires Quagga2 library for barcode detection
 */

class BarcodeScanner {
  constructor() {
    this.isScanning = false;
    this.stream = null;
    this.quaggaInitialized = false;
    this.onResult = null;
    this.onError = null;
  }

  /**
   * Check if camera scanning is supported
   * @returns {boolean}
   */
  isSupported() {
    // Check for WebRTC adapter availability and navigator.mediaDevices
    // Camera scanning is supported on both desktop and mobile browsers
    return (
      typeof adapter !== 'undefined' && 
      navigator.mediaDevices && 
      typeof navigator.mediaDevices.getUserMedia === 'function'
    );
  }

  /**
   * Get browser information using WebRTC adapter
   * @returns {object}
   */
  getBrowserInfo() {
    if (typeof adapter !== 'undefined' && adapter.browserDetails) {
      return {
        browser: adapter.browserDetails.browser,
        version: adapter.browserDetails.version
      };
    }
    return { browser: 'unknown', version: 0 };
  }

  /**
   * Get optimized camera constraints based on browser capabilities
   * @returns {object}
   */
  getCameraConstraints() {
    const browserInfo = this.getBrowserInfo();
    const isMobile = this.isMobileDevice();
    
    let constraints = {
      width: { min: 320, ideal: 640, max: 1920 },
      height: { min: 240, ideal: 480, max: 1080 },
      aspectRatio: { ideal: 1.333 }
    };

    // Set camera facing mode based on device type
    if (isMobile) {
      // On mobile, prefer back camera for barcode scanning
      constraints.facingMode = "environment";
      // Mobile-specific adjustments for better performance
      constraints.width = { min: 320, ideal: 480, max: 1280 };
      constraints.height = { min: 240, ideal: 360, max: 720 };
    } else {
      // On desktop, use any available camera (usually front-facing webcam)
      constraints.facingMode = "user";
    }

    // Browser-specific optimizations
    if (browserInfo.browser === 'safari') {
      // Safari sometimes has issues with high resolutions
      constraints.width = { min: 320, ideal: 480, max: 1280 };
      constraints.height = { min: 240, ideal: 360, max: 720 };
    } else if (browserInfo.browser === 'firefox') {
      // Firefox handles constraints differently
      constraints.frameRate = { ideal: 30, max: 60 };
    }

    return constraints;
  }

  /**
   * Check if we're on a mobile device
   * @returns {boolean}
   */
  isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  }

  /**
   * Initialize the barcode scanner
   * @param {HTMLElement} containerElement - Container element for the scanner
   * @param {function} onResult - Callback for successful scan
   * @param {function} onError - Callback for errors
   */
  async initialize(containerElement, onResult, onError) {
    this.onResult = onResult;
    this.onError = onError;

    if (!this.isSupported()) {
      if (onError) onError(new Error('Camera not supported on this device'));
      return false;
    }

    try {
      // Check if WebRTC adapter is available
      if (typeof adapter === 'undefined') {
        throw new Error('WebRTC adapter not loaded. Please ensure webrtc-adapter is included in your page.');
      }

      // Check if Quagga2 is available globally
      if (typeof Quagga === 'undefined') {
        throw new Error('Quagga2 library not loaded. Please ensure it is included in your page.');
      }

      // Log browser information for debugging
      const browserInfo = this.getBrowserInfo();
      console.log(`WebRTC adapter initialized: ${browserInfo.browser} v${browserInfo.version}`);

      return true;
    } catch (error) {
      if (onError) onError(error);
      return false;
    }
  }

  /**
   * Copy video frames to canvas continuously (based on Quagga2 docs pattern)
   * @param {HTMLVideoElement} video - The video element
   * @param {CanvasRenderingContext2D} ctx - Canvas 2D context
   */
  copyToCanvas(video, ctx) {
    const frame = () => {
      if (this.isScanning && video && ctx) {
        try {
          // Only draw if video has valid dimensions
          if (video.videoWidth > 0 && video.videoHeight > 0) {
            ctx.drawImage(video, 0, 0, ctx.canvas.width, ctx.canvas.height);
          }
        } catch (error) {
          console.warn('Canvas draw error:', error);
        }
        requestAnimationFrame(frame);
      }
    };
    frame();
  }

  /**
   * Capture current frame from canvas as data URL
   * @param {string} format - Image format (default: 'image/jpeg')
   * @param {number} quality - Image quality 0-1 (default: 0.8)
   * @returns {string|null} Data URL of captured frame
   */
  captureFrame(format = 'image/jpeg', quality = 0.8) {
    const previewCanvas = document.getElementById('preview-canvas');
    if (previewCanvas) {
      try {
        return previewCanvas.toDataURL(format, quality);
      } catch (error) {
        console.error('Error capturing frame:', error);
        return null;
      }
    }
    return null;
  }

  /**
   * Add scanning guides to help users position barcodes
   * @param {HTMLElement} container - The scanner container
   */
  addScanningGuides(container) {
    // Create scanning guide overlay
    const guide = document.createElement('div');
    guide.style.cssText = `
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 250px;
      height: 120px;
      border: 2px solid #ff0000;
      border-radius: 8px;
      pointer-events: none;
      z-index: 1000;
      box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.3);
    `;
    
    // Add corner indicators
    const corners = ['top-left', 'top-right', 'bottom-left', 'bottom-right'];
    corners.forEach(corner => {
      const cornerElement = document.createElement('div');
      cornerElement.style.cssText = `
        position: absolute;
        width: 20px;
        height: 20px;
        border: 3px solid #00ff00;
        ${corner.includes('top') ? 'top: -3px;' : 'bottom: -3px;'}
        ${corner.includes('left') ? 'left: -3px;' : 'right: -3px;'}
        ${corner.includes('top') && corner.includes('left') ? 'border-right: none; border-bottom: none;' : ''}
        ${corner.includes('top') && corner.includes('right') ? 'border-left: none; border-bottom: none;' : ''}
        ${corner.includes('bottom') && corner.includes('left') ? 'border-right: none; border-top: none;' : ''}
        ${corner.includes('bottom') && corner.includes('right') ? 'border-left: none; border-top: none;' : ''}
      `;
      guide.appendChild(cornerElement);
    });
    
    container.appendChild(guide);
  }

  /**
   * Start scanning
   * @param {HTMLElement} videoContainer - Container element for the scanner
   */
  async startScanning(videoContainer) {
    if (this.isScanning) return;

    try {
      this.isScanning = true;

      // Quagga2 configuration following the official example with WebRTC adapter optimizations
      const config = {
        inputStream: {
          name: "Live",
          type: "LiveStream",
          target: videoContainer, // Target the container, not the video element
          //constraints: this.getCameraConstraints(),
          singleChannel: false // Quagga2 feature for better performance
        },
        decoder: {
          readers: [
            "code_128_reader",
            "ean_reader", 
            "ean_8_reader",
            "code_39_reader",
            "code_39_vin_reader",
            "codabar_reader",
            "upc_reader",
            "upc_e_reader",
            "i2of5_reader" // Additional reader supported by Quagga2
          ],
          debug: {
            showCanvas: false,
            showPatches: false,
            showFoundPatches: false,
            showSkeleton: false,
            showLabels: false,
            showPatchLabels: false,
            showRemainingPatchLabels: false,
            boxFromPatches: {
              showTransformed: false,
              showTransformedBox: false,
              showBB: false
            }
          },
          multiple: false // Quagga2 feature - only detect one barcode at a time
        },
        locate: true,
        locator: {
          halfSample: true,
          patchSize: "medium",
          debug: {
            showCanvas: false,
            showPatches: false,
            showFoundPatches: false,
            showSkeleton: false,
            showLabels: false,
            showPatchLabels: false,
            showRemainingPatchLabels: false
          }
        },
        numOfWorkers: navigator.hardwareConcurrency > 1 ? 2 : 1, // Adaptive worker count
        frequency: 10
      };

      await new Promise((resolve, reject) => {
        Quagga.init(config, (err) => {
          if (err) {
            console.error('Quagga2 init error:', err);
            reject(err);
            return;
          }
          console.log('Quagga2 initialized successfully');
          resolve();
        });
      });

      Quagga.onDetected(this.handleDetection.bind(this));
      Quagga.start();
      
      // Set up canvas preview if available
      const previewCanvas = document.getElementById('preview-canvas');
      if (previewCanvas) {
        // Wait for video element to be created by Quagga2
        setTimeout(() => {
          const videoElement = videoContainer.querySelector('video');
          if (videoElement) {
            // Set canvas dimensions to match video
            previewCanvas.width = videoElement.videoWidth || 640;
            previewCanvas.height = videoElement.videoHeight || 480;
            
            // Start copying video frames to canvas
            const ctx = previewCanvas.getContext('2d');
            this.copyToCanvas(videoElement, ctx);
            
            console.log('Canvas preview initialized:', previewCanvas.width + 'x' + previewCanvas.height);
          }
        }, 1000); // Give Quagga2 time to initialize
      }
      
      // Add scanning guides
      this.addScanningGuides(videoContainer);
      
      this.quaggaInitialized = true;

    } catch (error) {
      console.error('Scanner start error:', error);
      this.isScanning = false;
      if (this.onError) this.onError(error);
    }
  }

  /**
   * Stop scanning
   */
  stopScanning() {
    if (!this.isScanning) return;

    try {
      if (this.quaggaInitialized) {
        Quagga.stop();
        // Quagga2 provides better cleanup
        Quagga.offDetected();
        Quagga.offProcessed();
        this.quaggaInitialized = false;
      }
    } catch (error) {
      console.warn('Error stopping Quagga2:', error);
    }

    this.isScanning = false;
  }

  /**
   * Handle barcode detection
   * @param {object} result - Quagga2 detection result
   */
  handleDetection(result) {
    if (!result || !result.codeResult) return;

    const code = result.codeResult.code;
    const format = result.codeResult.format;
    
    // Quagga2 provides better confidence scoring
    const startInfo = result.codeResult.startInfo;
    const decodedCodes = result.codeResult.decodedCodes;
    
    // Calculate confidence based on the number of successfully decoded patterns
    let confidence = 0;
    if (decodedCodes && decodedCodes.length > 0) {
      const validCodes = decodedCodes.filter(c => c.error !== undefined);
      confidence = validCodes.length / decodedCodes.length;
    }
    
    console.log(`Detected code: ${code}, format: ${format}, confidence: ${confidence.toFixed(2)}`);
    
    // More sophisticated validation with confidence threshold
    if (code && code.length >= 6 && confidence > 0.8) {
      // For numeric codes (GTINs), ensure they're digits
      if (/^\d+$/.test(code) && code.length >= 8) {
        console.log('Valid numeric barcode detected:', code);
        if (this.onResult) {
          this.onResult(code);
        }
        this.stopScanning();
      } 
      // For alphanumeric codes (could be GS1 format)
      else if (code.length >= 10) {
        console.log('Alphanumeric barcode detected:', code);
        if (this.onResult) {
          this.onResult(code);
        }
        this.stopScanning();
      }
    } else if (code && code.length >= 8 && confidence > 0.6) {
      // Lower confidence threshold for longer codes
      console.log('Medium confidence barcode detected:', code);
      if (this.onResult) {
        this.onResult(code);
      }
      this.stopScanning();
    }
  }

  /**
   * Create and show scanner modal
   * @param {function} onResult - Callback for successful scan
   * @param {function} onError - Callback for errors
   */
  showScannerModal(onResult, onError) {
    // Remove existing modal if present
    const existingModal = document.getElementById('barcode-scanner-modal');
    if (existingModal) {
      existingModal.remove();
    }

    // Create modal HTML
    const modalHTML = `
      <div id="barcode-scanner-modal" class="modal" tabindex="-1" style="display: block; background-color: rgba(0,0,0,0.8);">
        <div class="modal-dialog modal-lg">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Scan Barcode</h5>
              <button type="button" class="close" aria-label="Close">
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
            <div class="modal-body text-center">
              <div id="scanner-status" class="mb-3">
                <p class="text-muted">Initializing camera...</p>
              </div>
              <div id="scanner-container" style="position: relative; display: inline-block; border: 2px solid #007bff; border-radius: 8px; overflow: hidden; width: 640px; height: 480px; background: #000;">
              </div>
              <div class="mt-3">
                <p class="small text-muted">Position the barcode within the camera view</p>
                <p id="debug-info" class="small text-muted" style="font-family: monospace;"></p>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" id="scanner-close">Close</button>
            </div>
          </div>
        </div>
      </div>
    `;

    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    const modal = document.getElementById('barcode-scanner-modal');
    const scannerContainer = document.getElementById('scanner-container');
    const statusDiv = document.getElementById('scanner-status');
    const debugInfo = document.getElementById('debug-info');
    const closeBtn = document.getElementById('scanner-close');
    const closeBtnX = modal.querySelector('.close');

    // Update debug info
    const updateDebug = (message) => {
      if (debugInfo) {
        debugInfo.textContent = message;
      }
      console.log('[Scanner]', message);
    };

    // Close handlers
    const closeModal = () => {
      this.stopScanning();
      modal.remove();
    };

    closeBtn.addEventListener('click', closeModal);
    closeBtnX.addEventListener('click', closeModal);
    
    // Close on backdrop click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });

    // Initialize scanner
    const browserInfo = this.getBrowserInfo();
    updateDebug(`Initializing scanner on ${browserInfo.browser} v${browserInfo.version}...`);
    this.initialize(scannerContainer, (code) => {
      updateDebug(`Scanned: ${code}`);
      closeModal();
      if (onResult) onResult(code);
    }, (error) => {
      const errorMsg = `Error on ${browserInfo.browser}: ${error.message}`;
      statusDiv.innerHTML = `<p class="text-danger">${errorMsg}</p>`;
      updateDebug(errorMsg);
      if (onError) onError(error);
    }).then(async (success) => {
      if (success) {
        statusDiv.innerHTML = '<p class="text-success">Camera active - position barcode in view</p>';
        updateDebug('Starting Quagga2 camera...');
        await this.startScanning(scannerContainer);
        updateDebug('Quagga2 scanner ready');
        
        // Add scanning guides after Quagga2 has initialized
        this.addScanningGuides(scannerContainer);
      }
    }).catch((error) => {
      const errorMsg = `Initialization failed: ${error.message}`;
      statusDiv.innerHTML = `<p class="text-danger">${errorMsg}</p>`;
      updateDebug(errorMsg);
    });
  }
}

// Create global instance
window.BarcodeScanner = new BarcodeScanner();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = BarcodeScanner;
}