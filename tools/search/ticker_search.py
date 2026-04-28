"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get('query', '').strip()
        if len(query) < 2:
            return json.dumps({'error': 'query must be at least 2 characters', 'results': []})
        market = data.get('market', 'GLOBAL')
        asset_type = data.get('asset_type', 'all')
        limit = min(max(1, data.get('limit', 10)), 50)
        
        # Simulated realistic ticker database (in production would hit an API/database)
        ticker_db = [
            {'ticker': 'AAPL', 'name': 'Apple Inc.', 'exchange': 'NASDAQ', 'market': 'US', 'type': 'stock', 'sector': 'Technology'},
            {'ticker': 'MSFT', 'name': 'Microsoft Corporation', 'exchange': 'NASDAQ', 'market': 'US', 'type': 'stock', 'sector': 'Technology'},
            {'ticker': 'GOOGL', 'name': 'Alphabet Inc.', 'exchange': 'NASDAQ', 'market': 'US', 'type': 'stock', 'sector': 'Technology'},
            {'ticker': 'AMZN', 'name': 'Amazon.com Inc.', 'exchange': 'NASDAQ', 'market': 'US', 'type': 'stock', 'sector': 'Consumer Cyclical'},
            {'ticker': 'TSLA', 'name': 'Tesla Inc.', 'exchange': 'NASDAQ', 'market': 'US', 'type': 'stock', 'sector': 'Automotive'},
            {'ticker': 'BTC-USD', 'name': 'Bitcoin USD', 'exchange': 'CRYPTO', 'market': 'GLOBAL', 'type': 'index', 'sector': 'Cryptocurrency'},
            {'ticker': 'SPY', 'name': 'SPDR S&P 500 ETF Trust', 'exchange': 'NYSE Arca', 'market': 'US', 'type': 'etf', 'sector': 'Large Cap'},
            {'ticker': 'VWRL.AS', 'name': 'Vanguard FTSE All-World UCITS ETF', 'exchange': 'Euronext Amsterdam', 'market': 'EU', 'type': 'etf', 'sector': 'Global Equity'},
            {'ticker': '6758.T', 'name': 'Sony Group Corporation', 'exchange': 'Tokyo', 'market': 'ASIA', 'type': 'stock', 'sector': 'Technology'},
            {'ticker': 'BABA', 'name': 'Alibaba Group Holding Ltd', 'exchange': 'NYSE', 'market': 'US', 'type': 'stock', 'sector': 'Consumer Cyclical'}
        ]
        
        # Filter by query (name or ticker contains query, case-insensitive)
        query_lower = query.lower()
        filtered = [
            item for item in ticker_db
            if query_lower in item['name'].lower() or query_lower in item['ticker'].lower()
        ]
        
        # Filter by market
        if market != 'GLOBAL':
            filtered = [item for item in filtered if item['market'] == market]
        
        # Filter by asset type
        if asset_type != 'all':
            filtered = [item for item in filtered if item['type'] == asset_type]
        
        # Sort by relevance: exact ticker match first, then name starts with query, etc.
        def sort_key(item):
            ticker_lower = item['ticker'].lower()
            name_lower = item['name'].lower()
            score = 0
            if ticker_lower == query_lower:
                score -= 10
            elif name_lower.startswith(query_lower):
                score -= 5
            elif any(part.startswith(query_lower) for part in name_lower.replace(',', ' ').split()):
                score -= 2
            return score
        filtered.sort(key=sort_key)
        
        results = filtered[:limit]
        
        return json.dumps({
            'query': query,
            'count': len(results),
            'results': results
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e), 'results': []})


TOOL_SPEC = {
    "name": "ticker_search",
    "description": "Search for financial securities by company name, ticker symbol, or industry sector, returning matching ticker symbols, exchange, and company details for investment research or portfolio building.",
    "category": "search",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query string: company name (e.g. Apple), ticker symbol (e.g. AAPL), or partial name/symbol. Minimum 2 characters."
        },
        "market": {
            "type": "string",
            "description": "Optional: Filter by stock exchange or market region. Allowed values: US, EU, ASIA, GLOBAL.",
            "enum": [
                "US",
                "EU",
                "ASIA",
                "GLOBAL"
            ],
            "default": "GLOBAL"
        },
        "asset_type": {
            "type": "string",
            "description": "Optional: Filter by asset type. Allowed values: stock, etf, mutual_fund, index, all.",
            "enum": [
                "stock",
                "etf",
                "mutual_fund",
                "index",
                "all"
            ],
            "default": "all"
        },
        "limit": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (1-50). Default 10.",
            "minimum": 1,
            "maximum": 50,
            "default": 10
        }
    },
    "required": [
        "query"
    ]
},
}
