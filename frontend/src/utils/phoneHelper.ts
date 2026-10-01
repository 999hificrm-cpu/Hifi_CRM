/**
 * Universal Phone Helper for Indian (+91) 10-digit standardization.
 * 
 * Rules:
 * 1. Users only enter the 10-digit Indian number (e.g. 9876543210).
 * 2. Dashboards across the entire app display strictly the 10-digit number.
 * 3. The Call action (tel:) automatically attaches +91 internally without passing +91 into the 10-digit phone field.
 */

export const format10DigitPhone = (phone?: string | null): string => {
  if (!phone) return "";
  const str = String(phone).trim();

  // If phone has data masking asterisks (e.g. "9198****1234" or "+91 98**** 1234" or "98****1234")
  if (str.includes("*")) {
    let clean = str.replace(/^\+91[\s\-]*/, "");
    if (clean.startsWith("91") && clean.length > 10) {
      clean = clean.slice(2);
    }
    return clean.trim();
  }

  // Extract all digits
  const digits = str.replace(/\D/g, "");
  if (!digits) return "";

  // If 12 digits and starts with 91 (India country code) -> take last 10 digits
  if (digits.length === 12 && digits.startsWith("91")) {
    return digits.slice(2);
  }

  // If 11 digits and starts with 0 (STD trunk prefix) -> take last 10 digits
  if (digits.length === 11 && digits.startsWith("0")) {
    return digits.slice(1);
  }

  // If longer than 10 digits -> take last 10 digits
  if (digits.length > 10) {
    return digits.slice(-10);
  }

  // Already 10 digits or local format
  return digits;
};

export const getCallUrl = (phone?: string | null): string => {
  if (!phone) return "";
  const tenDigits = format10DigitPhone(phone).replace(/\D/g, "");
  if (!tenDigits) return "";
  // Internal automated +91 prefix for telecom dialers
  return `tel:+91${tenDigits}`;
};

export const getWhatsAppDigits = (phone?: string | null): string => {
  if (!phone) return "";
  const tenDigits = format10DigitPhone(phone).replace(/\D/g, "");
  if (!tenDigits) return "";
  return `91${tenDigits}`;
};

export const cleanPhoneInput = (val: string): string => {
  if (!val) return "";
  // Strip any characters that aren't digits, spaces, or hyphens
  const allowed = val.replace(/[^\d\s\-]/g, "");
  // Count digits in the allowed string
  const digits = allowed.replace(/\D/g, "");
  // If we have more than 10 digits, truncate to the 10th digit
  if (digits.length > 10) {
    let digitCount = 0;
    let result = "";
    for (let i = 0; i < allowed.length; i++) {
      const char = allowed[i];
      if (/\d/.test(char)) {
        digitCount++;
        if (digitCount > 10) break;
      }
      result += char;
    }
    return result;
  }
  return allowed;
};
