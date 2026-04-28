"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate valid International Bank Account Numbers (IBAN) for specified countries."""
    import json
    import random

    # Validate IBAN character conversion module
    def char_to_num(ch):
        return str(ord(ch.upper()) - 55)

    def mod97(iban_str):
        """Calculate mod 97 of an IBAN string (country code + check digits + BBAN)."""
        # Move first 4 characters to end
        rearranged = iban_str[4:] + iban_str[:4]
        # Convert letters to numbers
        numeric = ''.join(char_to_num(c) if c.isalpha() else c for c in rearranged)
        # Compute mod 97
        return int(numeric) % 97

    def calculate_check_digits(bban, country_code):
        """Compute the two check digits for an IBAN given BBAN and country code."""
        # Temporary IBAN with '00' as check digits
        temp_iban = country_code + '00' + bban
        # Calculate what check digit makes mod 97 = 1
        remainder = mod97(temp_iban)
        check_digits = 98 - remainder
        # Format check digits with leading zero if needed
        return f"{check_digits:02d}"

    def generate_iban(country_code, bank_code, account_number):
        """Generate a full IBAN string given components."""
        # Build BBAN based on country
        bban = ''
        if country_code == 'DE':
            bban = bank_code + account_number.zfill(10)
        elif country_code == 'GB':
            bban = bank_code + account_number.zfill(8)
        elif country_code == 'FR':
            bban = bank_code + account_number.zfill(11) + '00000'
        elif country_code == 'IT':
            bban = bank_code + '12345' + account_number.zfill(10)
        elif country_code == 'ES':
            bban = bank_code + '1234' + account_number.zfill(10)
        elif country_code == 'NL':
            bban = bank_code + account_number.zfill(10)
        elif country_code == 'BE':
            bban = bank_code + account_number.zfill(9)
        elif country_code == 'CH':
            bban = bank_code + account_number.zfill(12)
        elif country_code == 'AT':
            bban = bank_code + account_number.zfill(11)
        elif country_code == 'LU':
            bban = bank_code + account_number.zfill(13)
        elif country_code == 'IE':
            bban = bank_code + '123456' + account_number.zfill(8)
        else:
            raise ValueError(f"Unsupported country code: {country_code}")

        check = calculate_check_digits(bban, country_code)
        full_iban = country_code + check + bban
        # Validate (should be 1)
        if mod97(full_iban) != 1:
            raise RuntimeError("IBAN validation failed after generation")
        return full_iban

    # Country-specific bank code generators for random
    RANDOM_BANK_CODES = {
        'DE': ['10010010', '20020020', '30010030', '40040040', '50010517'],
        'GB': ['400300', '200000', '601613', '309634', '238509'],
        'FR': ['30004', '30066', '20041', '10096', '10278'],
        'IT': ['03069', '03111', '03022', '03071', '02008'],
        'ES': ['2100', '0049', '0182', '2038', '0128'],
        'NL': ['ABNA', 'INGB', 'RABO', 'BUNQ', 'KNAB'],
        'BE': ['001', '068', '523', '363', '751'],
        'CH': ['084', '092', '048', '058', '090'],
        'AT': ['12000', '14000', '16000', '17000', '19000'],
        'LU': ['001', '002', '003', '004', '005'],
        'IE': ['AIBK', 'BOFI', 'BANK', 'ULSB', 'KBCI']
    }

    try:
        data = json.loads(payload)
        country_code = data.get('country_code')
        if not country_code or not isinstance(country_code, str) or len(country_code) != 2:
            return json.dumps({'error': 'Invalid or missing country_code (must be 2-letter ISO code)'})
        country_code = country_code.upper()
        if country_code not in RANDOM_BANK_CODES:
            return json.dumps({'error': f'Unsupported country_code: {country_code}'})

        quantity = data.get('quantity', 1)
        if not isinstance(quantity, int) or quantity < 1 or quantity > 100:
            return json.dumps({'error': 'quantity must be an integer between 1 and 100'})

        random_bank = data.get('random_bank', False)
        bank_code = data.get('bank_code')
        account_number = data.get('account_number')

        if not random_bank and not bank_code:
            return json.dumps({'error': 'bank_code is required unless random_bank is true'})

        # Normalize bank code (may be letters)
        if bank_code:
            bank_code = bank_code.strip()
        else:
            bank_code = random.choice(RANDOM_BANK_CODES[country_code])

        # Generate IBAN(s)
        ibans = []
        for i in range(quantity):
            if quantity > 1:
                # Auto-generate account number based on iteration
                if account_number:
                    base = int(account_number) if account_number.isdigit() else 0
                    new_acct = str(base + i).zfill(10)
                else:
                    new_acct = str(random.randint(100000000, 9999999999)).zfill(10)
            else:
                new_acct = account_number if account_number else ''.join([str(random.randint(0,9)) for _ in range(10)])

            iban_str = generate_iban(country_code, bank_code, new_acct)
            ibans.append(iban_str)

        result = {
            'generated_ibans': ibans,
            'count': len(ibans),
            'country': country_code,
            'bank_code_used': bank_code
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "iban_generator",
    "description": "Generate valid International Bank Account Numbers (IBANs) for specified countries, including the two-letter country code, check digits, and basic bank account number (BBAN) segment, complying with ISO 13616 standards, and optionally producing multiple IBANs in bulk. Returns the generated IBAN(s) and their corresponding country, bank identifier, and branch code.",
    "category": "generate",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "country_code": {
            "type": "string",
            "description": "Two-letter ISO 3166-1 alpha-2 country code (e.g., DE for Germany, GB for United Kingdom, FR for France). Must be an uppercase string. Supported codes: DE, GB, FR, IT, ES, NL, BE, CH, AT, LU, IE.",
            "minLength": 2,
            "maxLength": 2
        },
        "bank_code": {
            "type": "string",
            "description": "National bank identifier for the specified country. For DE: 8-digit bankleitzahl. For GB: 6-digit sort code (e.g., 200000). For FR: 5-digit bank code. For IT: 5-digit ABI code. For ES: 4-digit entity code. For NL: 4-letter bank code (e.g., RABO). For BE: 3-digit bank code. For CH: 3-5 digits bank clearing number. For AT: 5-digit bank code. For LU: 3-digit bank code. For IE: 4-character bank code (e.g., AIBK). Required for single generation; optional for random generation if random_bank is True."
        },
        "account_number": {
            "type": "string",
            "description": "Customer account number (digits only). Varies in length by country (e.g., DE: up to 10 digits, GB: 8 digits, FR: 11 digits). Optional: if not provided, a valid random account number will be generated."
        },
        "quantity": {
            "type": "integer",
            "description": "Optional: number of unique IBANs to generate (1-100). Default is 1. If >1, account numbers will be auto-generated sequentially or randomly to ensure uniqueness.",
            "minimum": 1,
            "maximum": 100,
            "default": 1
        },
        "random_bank": {
            "type": "boolean",
            "description": "Optional: if True, a random valid bank code for the country will be used instead of requiring bank_code. Default is False.",
            "default": False
        }
    },
    "required": [
        "country_code"
    ]
},
}
