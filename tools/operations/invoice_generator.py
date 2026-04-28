"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime

    try:
        data = json.loads(payload)
        # Validate required fields
        required = ['customer_name', 'customer_email', 'invoice_date', 'due_date', 'line_items']
        for field in required:
            if field not in data:
                return json.dumps({'error': f'Missing required field: {field}'}, ensure_ascii=False)
        
        customer_name = data['customer_name']
        customer_email = data['customer_email']
        invoice_date = data['invoice_date']
        due_date = data['due_date']
        line_items = data['line_items']
        currency = data.get('currency', 'USD')
        notes = data.get('notes', '')

        # Validate date formats
        try:
            datetime.strptime(invoice_date, '%Y-%m-%d')
            datetime.strptime(due_date, '%Y-%m-%d')
        except ValueError:
            return json.dumps({'error': 'Invalid date format. Use YYYY-MM-DD.'}, ensure_ascii=False)

        if not line_items or not isinstance(line_items, list):
            return json.dumps({'error': 'line_items must be a non-empty array'}, ensure_ascii=False)

        subtotal = 0.0
        total_tax = 0.0
        processed_items = []

        for idx, item in enumerate(line_items):
            if 'description' not in item or 'quantity' not in item or 'unit_price' not in item:
                return json.dumps({'error': f'Item {idx} missing required fields: description, quantity, unit_price'}, ensure_ascii=False)
            desc = item['description']
            qty = item['quantity']
            unit_price = item['unit_price']
            tax_rate = item.get('tax_rate', 0.0)

            if not isinstance(qty, (int, float)) or qty <= 0:
                return json.dumps({'error': f'Item {idx}: quantity must be a positive number'}, ensure_ascii=False)
            if not isinstance(unit_price, (int, float)) or unit_price < 0:
                return json.dumps({'error': f'Item {idx}: unit_price must be a non-negative number'}, ensure_ascii=False)
            if not isinstance(tax_rate, (int, float)) or tax_rate < 0:
                return json.dumps({'error': f'Item {idx}: tax_rate must be a non-negative number'}, ensure_ascii=False)

            line_total = qty * unit_price
            line_tax = line_total * (tax_rate / 100.0)
            subtotal += line_total
            total_tax += line_tax

            processed_items.append({
                'description': desc,
                'quantity': qty,
                'unit_price': unit_price,
                'tax_rate': tax_rate,
                'line_total': round(line_total, 2),
                'line_tax': round(line_tax, 2)
            })

        grand_total = subtotal + total_tax

        invoice = {
            'customer_name': customer_name,
            'customer_email': customer_email,
            'invoice_date': invoice_date,
            'due_date': due_date,
            'currency': currency,
            'notes': notes,
            'line_items': processed_items,
            'subtotal': round(subtotal, 2),
            'total_tax': round(total_tax, 2),
            'grand_total': round(grand_total, 2)
        }

        return json.dumps(invoice, ensure_ascii=False, default=str)
    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "invoice_generator",
    "description": "Create a professional invoice with line items, tax calculations, and total amounts for customer billing and record-keeping. Returns the invoice details including due date, subtotal, tax, and grand total.",
    "category": "operations",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "customer_name": {
            "type": "string",
            "description": "Full name of the customer or client being billed"
        },
        "customer_email": {
            "type": "string",
            "description": "Email address of the customer for invoice delivery"
        },
        "invoice_date": {
            "type": "string",
            "description": "Date the invoice is issued, format YYYY-MM-DD"
        },
        "due_date": {
            "type": "string",
            "description": "Date by which payment is due, format YYYY-MM-DD"
        },
        "line_items": {
            "type": "array",
            "description": "List of products or services being billed",
            "items": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Name or description of the product/service"
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Number of units purchased (positive integer)"
                    },
                    "unit_price": {
                        "type": "number",
                        "description": "Price per unit in the currency (e.g., USD dollars, positive number)"
                    },
                    "tax_rate": {
                        "type": "number",
                        "description": "Optional: Tax rate as a percentage (e.g., 10 for 10%), default 0"
                    }
                },
                "required": [
                    "description",
                    "quantity",
                    "unit_price"
                ]
            }
        },
        "currency": {
            "type": "string",
            "description": "Optional: Currency code for the invoice (e.g., USD, EUR, GBP), default USD"
        },
        "notes": {
            "type": "string",
            "description": "Optional: Additional notes or payment instructions for the customer"
        }
    },
    "required": [
        "customer_name",
        "customer_email",
        "invoice_date",
        "due_date",
        "line_items"
    ]
},
}
