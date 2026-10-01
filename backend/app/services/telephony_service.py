import phonenumbers
from typing import Optional, Tuple

def parse_and_format_phone(phone_raw: str, default_region: str = "IN") -> Tuple[Optional[str], str, bool]:
    """
    Parses a phone number, formats it to E.164, and determines its type.
    Returns: (e164_formatted_number, phone_type, is_sms_capable)
    phone_type: MOBILE, LANDLINE, UNKNOWN, INVALID
    """
    if not phone_raw or not str(phone_raw).strip():
        return None, "UNKNOWN", False
        
    val = str(phone_raw).strip()
    # Remove floating point decimals from Excel like 9876543210.0
    if val.endswith(".0"):
        val = val[:-2]
        
    try:
        parsed = phonenumbers.parse(val, default_region)
        if not phonenumbers.is_valid_number(parsed):
            return None, "INVALID", False
            
        e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        
        num_type = phonenumbers.number_type(parsed)
        if num_type == phonenumbers.PhoneNumberType.MOBILE:
            return e164, "MOBILE", True
        elif num_type == phonenumbers.PhoneNumberType.FIXED_LINE:
            return e164, "LANDLINE", False
        elif num_type == phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE:
            return e164, "MOBILE", True
        else:
            return e164, "UNKNOWN", False
            
    except phonenumbers.NumberParseException:
        # Fallback regex for Indian numbers if phonenumbers library fails
        digits = ''.join(c for c in val if c.isdigit())
        if len(digits) >= 10:
            last_10 = digits[-10:]
            if last_10[0] in ['6', '7', '8', '9']:
                return f"+91{last_10}", "MOBILE", True
            else:
                return f"+91{last_10}", "LANDLINE", False
        return None, "INVALID", False
