"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random
    import string
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        path = data.get('path')
        method = data.get('method')
        status_code = data.get('status_code')
        if not path or not method or not status_code:
            return json.dumps({'error': 'Missing required fields: path, method, status_code'}, ensure_ascii=False)
        # Infer entity type from path
        entity_type = data.get('entity_type', 'auto')
        if entity_type == 'auto':
            segs = [s for s in path.split('/') if s and not s.startswith('{')]
            if 'users' in segs:
                entity_type = 'user'
            elif 'orders' in segs:
                entity_type = 'order'
            elif 'products' in segs:
                entity_type = 'product'
            else:
                entity_type = 'custom'
        count = data.get('count', 3 if method == 'GET' else 1)
        count = max(1, min(50, count))
        custom_fields = data.get('custom_fields', {})
        include_timestamps = data.get('include_timestamps', False)
        def gen_id():
            return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        def gen_date():
            d = datetime.now() - timedelta(days=random.randint(0, 365))
            return d.isoformat()[:10]
        def mock_item(etype, idx):
            if etype == 'user':
                item = {
                    'id': gen_id(),
                    'name': f'User{idx}',
                    'email': f'user{idx}@example.com',
                    'role': random.choice(['admin','editor','viewer']),
                    'active': random.choice([True, False])
                }
            elif etype == 'order':
                item = {
                    'id': gen_id(),
                    'product_id': gen_id(),
                    'quantity': random.randint(1, 100),
                    'total': round(random.uniform(10.0, 5000.0), 2),
                    'status': random.choice(['pending','shipped','delivered','cancelled'])
                }
            elif etype == 'product':
                item = {
                    'id': gen_id(),
                    'name': f'Product_{idx}',
                    'price': round(random.uniform(1.99, 999.99), 2),
                    'category': random.choice(['electronics','books','clothing','home']),
                    'in_stock': random.choice([True, False])
                }
            else:
                item = {'id': gen_id()}
                for fname, ftype in custom_fields.items():
                    if ftype == 'string':
                        item[fname] = ''.join(random.choices(string.ascii_letters, k=10))
                    elif ftype == 'number':
                        item[fname] = round(random.uniform(0, 1000), 2)
                    elif ftype == 'boolean':
                        item[fname] = random.choice([True, False])
                    elif ftype == 'date':
                        item[fname] = gen_date()
            if include_timestamps:
                item['created_at'] = datetime.now().isoformat()
                item['updated_at'] = datetime.now().isoformat()
            return item
        items = [mock_item(entity_type, i) for i in range(count)]
        result = {
            'status': status_code,
            'headers': {
                'content-type': 'application/json',
                'x-request-id': gen_id()
            },
            'data': items if len(items) > 1 else (items[0] if items else None)
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "generate_api_response",
    "description": "Generate a realistic mock API response for any HTTP endpoint: given a request path, method, status code, and optional parameter overrides, returns a JSON body with status, headers, and a body placeholder filled with generated mock data entities (users, orders, products, or custom types).",
    "category": "generate",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Request URL path, e.g., /api/v2/users. Used to infer default entity type (users, orders, products)."
        },
        "method": {
            "type": "string",
            "enum": [
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "PATCH"
            ],
            "description": "HTTP method for the response."
        },
        "status_code": {
            "type": "integer",
            "description": "HTTP status code, e.g., 200, 404, 500. Must be between 100 and 599.",
            "minimum": 100,
            "maximum": 599
        },
        "entity_type": {
            "type": "string",
            "enum": [
                "auto",
                "user",
                "order",
                "product",
                "custom"
            ],
            "description": "Optional: Override the entity type derived from the path. 'auto' will infer from path segments. 'custom' requires custom_fields parameter."
        },
        "count": {
            "type": "integer",
            "description": "Optional: Number of mock items to generate (1–50). Default is 1 for single-entity endpoints, 3 for list endpoints.",
            "minimum": 1,
            "maximum": 50
        },
        "custom_fields": {
            "type": "object",
            "description": "Optional: For 'custom' entity_type, define field name and a type hint (string, number, boolean, date). Example: {\"session_id\": \"string\", \"score\": \"number\"}.",
            "additionalProperties": {
                "type": "string",
                "enum": [
                    "string",
                    "number",
                    "boolean",
                    "date"
                ]
            }
        },
        "include_timestamps": {
            "type": "boolean",
            "description": "Optional: If True, adds created_at and updated_at fields to each item. Default False."
        }
    },
    "required": [
        "path",
        "method",
        "status_code"
    ]
},
}
