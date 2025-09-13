/**
 * GTIN Parser with GS1 Application Identifier Support
 * Handles parsing of GTIN codes that may include GS1 AIs for GTIN (01), Lot (10), and Expiration (17)
 */

class GTINParser {
  constructor() {
    // GS1 Application Identifiers we support
    this.supportedAIs = {
      '01': { name: 'GTIN', length: 14, fixed: true },
      '10': { name: 'Lot', length: 20, fixed: false },
      '17': { name: 'Expiration', length: 6, fixed: true }
    };
  }

  /**
   * Parse a barcode string that may contain GS1 AIs
   * @param {string} barcodeString - The raw barcode string
   * @returns {object} Parsed data with gtin, lot, expiration fields
   */
  parseBarcode(barcodeString) {
    if (!barcodeString || typeof barcodeString !== 'string') {
      return { gtin: '', lot: '', expiration: '', isGS1: false };
    }

    const trimmed = barcodeString.trim();
    
    // Check if this looks like a GS1 barcode (starts with parentheses or contains AI patterns)
    if (this.isGS1Format(trimmed)) {
      return this.parseGS1Barcode(trimmed);
    } else {
      // Plain GTIN - return as-is
      return { 
        gtin: trimmed, 
        lot: '', 
        expiration: '', 
        isGS1: false,
        original: trimmed
      };
    }
  }

  /**
   * Check if the string appears to be in GS1 format
   * @param {string} str - The string to check
   * @returns {boolean}
   */
  isGS1Format(str) {
    // Check for parentheses format: (01)12345678901234(17)220630(10)ABC123
    if (str.includes('(') && str.includes(')')) {
      return true;
    }
    
    // Check for raw GS1 format starting with known AIs
    for (const ai of Object.keys(this.supportedAIs)) {
      if (str.startsWith(ai)) {
        return true;
      }
    }
    
    return false;
  }

  /**
   * Parse a GS1 formatted barcode
   * @param {string} barcodeString - The GS1 barcode string
   * @returns {object} Parsed data
   */
  parseGS1Barcode(barcodeString) {
    const result = { 
      gtin: '', 
      lot: '', 
      expiration: '', 
      isGS1: true,
      original: barcodeString,
      errors: []
    };

    let workingString = barcodeString;

    // Handle parentheses format first
    if (workingString.includes('(') && workingString.includes(')')) {
      const aiMatches = workingString.match(/\((\d+)\)([^(]*)/g);
      if (aiMatches) {
        for (const match of aiMatches) {
          const aiMatch = match.match(/\((\d+)\)(.+)/);
          if (aiMatch) {
            const ai = aiMatch[1];
            const value = aiMatch[2];
            this.processAI(ai, value, result);
          }
        }
        return result;
      }
    }

    // Handle raw format (no parentheses)
    let position = 0;
    while (position < workingString.length) {
      let foundAI = false;
      
      // Try to match known AIs at current position
      for (const [ai, config] of Object.entries(this.supportedAIs)) {
        if (workingString.substr(position, ai.length) === ai) {
          position += ai.length;
          let value;
          
          if (config.fixed) {
            // Fixed length AI
            value = workingString.substr(position, config.length);
            position += config.length;
          } else {
            // Variable length AI - read until next AI or end
            let endPos = position;
            while (endPos < workingString.length) {
              let nextAIFound = false;
              for (const nextAI of Object.keys(this.supportedAIs)) {
                if (workingString.substr(endPos, nextAI.length) === nextAI) {
                  nextAIFound = true;
                  break;
                }
              }
              if (nextAIFound) break;
              endPos++;
            }
            value = workingString.substr(position, endPos - position);
            position = endPos;
          }
          
          this.processAI(ai, value, result);
          foundAI = true;
          break;
        }
      }
      
      if (!foundAI) {
        // Skip unknown character
        position++;
      }
    }

    return result;
  }

  /**
   * Process a single AI and its value
   * @param {string} ai - The Application Identifier
   * @param {string} value - The value for this AI
   * @param {object} result - The result object to populate
   */
  processAI(ai, value, result) {
    switch (ai) {
      case '01':
        result.gtin = value.trim();
        break;
      case '10':
        result.lot = value.trim();
        break;
      case '17':
        // Convert YYMMDD to YYYY-MM-DD format for HTML date input
        if (value && value.length === 6) {
          try {
            const year = parseInt(value.substr(0, 2));
            const month = value.substr(2, 2);
            const day = value.substr(4, 2);
            
            // Assume 21st century for years 00-29, 20th century for 30-99
            const fullYear = year <= 29 ? 2000 + year : 1900 + year;
            result.expiration = `${fullYear}-${month}-${day}`;
          } catch (e) {
            result.errors.push(`Invalid expiration date format: ${value}`);
          }
        } else {
          result.errors.push(`Invalid expiration date length: ${value}`);
        }
        break;
      default:
        // Unknown AI - ignore for now
        break;
    }
  }

  /**
   * Validate a GTIN
   * @param {string} gtin - The GTIN to validate
   * @returns {boolean}
   */
  validateGTIN(gtin) {
    if (!gtin || typeof gtin !== 'string') return false;
    
    const cleaned = gtin.replace(/\D/g, ''); // Remove non-digits
    
    // GTIN should be 8, 12, 13, or 14 digits
    if (![8, 12, 13, 14].includes(cleaned.length)) return false;
    
    // Basic checksum validation for GTIN-13 and GTIN-14
    if (cleaned.length === 13 || cleaned.length === 14) {
      return this.validateGTINChecksum(cleaned);
    }
    
    return true; // For GTIN-8 and GTIN-12, just check length
  }

  /**
   * Validate GTIN checksum
   * @param {string} gtin - The GTIN to validate
   * @returns {boolean}
   */
  validateGTINChecksum(gtin) {
    const digits = gtin.split('').map(Number);
    const checkDigit = digits.pop();
    
    let sum = 0;
    for (let i = 0; i < digits.length; i++) {
      const multiplier = (digits.length - i) % 2 === 0 ? 1 : 3;
      sum += digits[i] * multiplier;
    }
    
    const calculatedCheckDigit = (10 - (sum % 10)) % 10;
    return calculatedCheckDigit === checkDigit;
  }

  /**
   * Format expiration date for display
   * @param {string} dateString - Date in YYYY-MM-DD format
   * @returns {string} Formatted date
   */
  formatExpirationDate(dateString) {
    if (!dateString) return '';
    
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString();
    } catch (e) {
      return dateString;
    }
  }
}

// Create global instance
window.GTINParser = new GTINParser();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = GTINParser;
}