import re
from datetime import datetime
from typing import List, Dict, Any
PATTERNS: Dict[str, str] = {'PHONE': '(?:(?:\\+?91[\\-\\s]?)|0)?[6-9]\\d{9}\\b', 'VEHICLE': '\\b[A-Z]{2}[\\s\\-]?\\d{1,2}[\\s\\-]?[A-Z]{1,3}[\\s\\-]?\\d{4}\\b', 'IFSC': '\\b[A-Z]{4}0[A-Z0-9]{6}\\b', 'BANK_ACCOUNT': '(?:a/c|acc(?:ount)?)\\.?\\s*(?:no\\.?|number)?\\s*[:#]?\\s*(\\d{9,18})\\b', 'MONEY': '(?:(?:₹|\\bRs\\.?|\\bINR)\\s?\\d[\\d,]*(?:\\.\\d{1,2})?|\\b\\d+(?:\\.\\d+)?\\s?(?:lakh|lakhs|crore|crores)\\b)', 'ALIAS_MARKER': '(?:\\balias\\b|\\burf\\b|उर्फ)\\s+([A-Z][\\w.]+(?:\\s+[A-Z][\\w.]+)?)', 'EMAIL': '\\b[\\w\\.\\-\\+]+@[\\w\\-]+\\.[\\w\\.\\-]+\\b', 'IMEI': '\\bIMEI\\s*[:#]?\\s*(\\d{15})\\b', 'SOCIAL_HANDLE': '(?<![\\w.])@([A-Za-z][\\w.]{2,29})\\b', 'DATE': '\\b(?:\\d{1,2}[\\/\\-\\.]\\d{1,2}[\\/\\-\\.]\\d{2,4}|\\d{1,2}\\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\\.?\\s+\\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\\.?\\s+\\d{1,2},?\\s+\\d{4})\\b'}
CONFIDENCE = {'ALIAS_MARKER': 0.9, 'IMEI': 0.98, 'SOCIAL_HANDLE': 0.94, 'PHONE': 0.97, 'VEHICLE': 0.93, 'IFSC': 0.99, 'BANK_ACCOUNT': 0.95, 'MONEY': 0.96, 'EMAIL': 0.99, 'DATE': 0.9}
_MONTHS = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}

def normalize_phone(raw: str) -> str:
    digits = re.sub('\\D', '', raw)
    return '+91' + digits[-10:]

def normalize_vehicle(raw: str) -> str:
    return re.sub('[\\s\\-]', '', raw).upper()

def normalize_money(raw: str) -> str:
    low = raw.lower()
    mult = 100000 if 'lakh' in low else 10000000 if 'crore' in low else 1
    low = re.sub('(?:₹|rs\\.?|inr)', ' ', low)
    num = re.sub('(?<=\\d),(?=\\d)', '', low)
    num = re.sub('[^\\d\\.]', '', num)
    if not num:
        return raw
    try:
        return f'{float(num) * mult:.2f}'
    except ValueError:
        return raw

def normalize_date(raw: str) -> str:
    s = raw.strip().replace(',', '')
    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%d/%m/%y', '%d-%m-%y', '%d %B %Y', '%d %b %Y', '%B %d %Y', '%b %d %Y'):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return raw
NORMALIZERS = {'ALIAS_MARKER': lambda s: s, 'IMEI': lambda s: s, 'SOCIAL_HANDLE': lambda s: '@' + s.lower(), 'PHONE': normalize_phone, 'VEHICLE': normalize_vehicle, 'MONEY': normalize_money, 'DATE': normalize_date, 'IFSC': lambda s: s.upper(), 'BANK_ACCOUNT': lambda s: s, 'EMAIL': lambda s: s.lower()}
VEHICLE_BLOCKLIST = re.compile('\\b(?:FIR|IPC|CrPC|Sec|Section|U/S)\\b', re.I)

def extract_regex_entities(text: str) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for etype, pattern in PATTERNS.items():
        flags = re.IGNORECASE if etype in ('BANK_ACCOUNT', 'MONEY', 'DATE', 'ALIAS_MARKER', 'IMEI') else 0
        for m in re.finditer(pattern, text, flags):
            value = m.group(1) if m.groups() else m.group(0)
            start = m.start(1) if m.groups() else m.start()
            end = m.end(1) if m.groups() else m.end()
            if etype == 'VEHICLE':
                window = text[max(0, start - 25):start]
                if VEHICLE_BLOCKLIST.search(window):
                    continue
            out_type = 'PERSON' if etype == 'ALIAS_MARKER' else etype
            found.append({'type': out_type, 'alias_marked': etype == 'ALIAS_MARKER', 'value': value.strip(), 'normalized': NORMALIZERS.get(etype, lambda s: s)(value.strip()), 'confidence': CONFIDENCE[etype], 'extractor': 'regex', 'spans': [{'start': start, 'end': end}]})
    return found
if __name__ == '__main__':
    import json
    sample = 'On 14/01/2026 accused Rakesh Yadav (a/c no. 20345678901, IFSC SBIN0001234) transferred Rs. 2,50,000 to 9830012345 and fled in WB 02 AB 1234.'
    print(json.dumps(extract_regex_entities(sample), indent=2))