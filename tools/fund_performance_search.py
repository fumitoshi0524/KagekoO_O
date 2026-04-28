"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for mutual funds and ETFs by name, ticker, or asset class and retrieve their historical performance metrics."""
    import json
    from datetime import datetime, timedelta
    import random
    
    try:
        data = json.loads(payload)
        
        # Validate required inputs
        if 'query' not in data or 'search_type' not in data:
            return json.dumps({'error': 'Missing required fields: query, search_type'}, ensure_ascii=False)
        
        query = data['query'].strip()
        search_type = data['search_type']
        
        if search_type not in ['name', 'ticker', 'asset_class']:
            return json.dumps({'error': 'Invalid search_type. Must be name, ticker, or asset_class.'}, ensure_ascii=False)
        
        if not query and search_type != 'asset_class':
            return json.dumps({'error': 'Query cannot be empty for name or ticker search.'}, ensure_ascii=False)
        
        time_period = data.get('time_period', '1Y')
        if time_period not in ['1M', '3M', 'YTD', '1Y', '3Y', '5Y']:
            return json.dumps({'error': 'Invalid time_period. Must be 1M, 3M, YTD, 1Y, 3Y, or 5Y.'}, ensure_ascii=False)
        
        max_results = min(data.get('max_results', 10), 50)
        
        # Simulate fund database (in production, this would query an actual fund database/API)
        fund_database = [
            {'name': 'Vanguard Total Stock Market Index Fund', 'ticker': 'VTSAX', 'asset_class': 'equity', 'category': 'large_blend'},
            {'name': 'Fidelity Contrafund', 'ticker': 'FCNTX', 'asset_class': 'equity', 'category': 'large_growth'},
            {'name': 'PIMCO Total Return Fund', 'ticker': 'PTTRX', 'asset_class': 'bond', 'category': 'intermediate_core'},
            {'name': 'Vanguard Total Bond Market Index Fund', 'ticker': 'VBTLX', 'asset_class': 'bond', 'category': 'intermediate_core'},
            {'name': 'Fidelity Government Money Market Fund', 'ticker': 'SPRXX', 'asset_class': 'money_market', 'category': 'government'},
            {'name': 'Vanguard Wellington Fund', 'ticker': 'VWELX', 'asset_class': 'hybrid', 'category': 'balanced'},
            {'name': 'T. Rowe Price Blue Chip Growth Fund', 'ticker': 'TRBCX', 'asset_class': 'equity', 'category': 'large_growth'},
            {'name': 'Dodge & Cox Income Fund', 'ticker': 'DODIX', 'asset_class': 'bond', 'category': 'intermediate_core'},
            {'name': 'Vanguard 500 Index Fund', 'ticker': 'VFIAX', 'asset_class': 'equity', 'category': 'large_blend'},
            {'name': 'American Funds Growth Fund of America', 'ticker': 'AGTHX', 'asset_class': 'equity', 'category': 'large_growth'},
            {'name': 'iShares Core S&P 500 ETF', 'ticker': 'IVV', 'asset_class': 'equity', 'category': 'large_blend'},
            {'name': 'Vanguard Total International Stock Index Fund', 'ticker': 'VTIAX', 'asset_class': 'equity', 'category': 'foreign_large_blend'},
            {'name': 'Fidelity US Bond Index Fund', 'ticker': 'FXNAX', 'asset_class': 'bond', 'category': 'intermediate_core'},
            {'name': 'Vanguard Real Estate Index Fund', 'ticker': 'VGSLX', 'asset_class': 'equity', 'category': 'real_estate'},
            {'name': 'T. Rowe Price New Horizons Fund', 'ticker': 'PRNHX', 'asset_class': 'equity', 'category': 'small_growth'}
        ]
        
        # Search logic
        results = []
        query_lower = query.lower()
        
        for fund in fund_database:
            if search_type == 'name':
                if query_lower in fund['name'].lower():
                    results.append(fund)
            elif search_type == 'ticker':
                if query_lower == fund['ticker'].lower():
                    results.append(fund)
            elif search_type == 'asset_class':
                asset_class = data.get('asset_class', query).lower()
                if asset_class == fund['asset_class'].lower():
                    results.append(fund)
        
        # Limit results
        results = results[:max_results]
        
        if not results:
            return json.dumps({'results': [], 'total_count': 0, 'message': 'No funds found matching your search.'}, ensure_ascii=False)
        
        # Generate performance metrics for each fund
        time_multipliers = {'1M': 1, '3M': 3, 'YTD': 6, '1Y': 12, '3Y': 36, '5Y': 60}
        multiplier = time_multipliers[time_period]
        
        enriched_results = []
        for fund in results:
            # Simulate realistic performance data based on asset class
            base_return = random.uniform(-5, 15) if fund['asset_class'] == 'equity' else random.uniform(-2, 8)
            base_nav = random.uniform(10, 200)
            base_expense = random.uniform(0.03, 1.5) if fund['asset_class'] == 'equity' else random.uniform(0.02, 1.0)
            base_risk = random.uniform(1, 5)
            
            # Scale return by time period
            scaled_return = round(base_return * (multiplier / 12), 2) if time_period != 'YTD' else round(base_return * 0.6, 2)
            
            fund_data = {
                'name': fund['name'],
                'ticker': fund['ticker'],
                'asset_class': fund['asset_class'],
                'category': fund['category'],
                'nav': round(base_nav, 2),
                'nav_date': datetime.now().strftime('%Y-%m-%d'),
                'return_' + time_period.lower(): scaled_return,
                'expense_ratio': round(base_expense, 2),
                'risk_rating': min(5, round(base_risk, 1)),
                'time_period': time_period
            }
            enriched_results.append(fund_data)
        
        # Sort by relevance (exact ticker match first, then by name match score)
        if search_type == 'ticker':
            enriched_results.sort(key=lambda x: x['ticker'].lower() == query_lower, reverse=True)
        
        result = {
            'results': enriched_results,
            'total_count': len(enriched_results),
            'search_params': {
                'query': query,
                'search_type': search_type,
                'time_period': time_period
            },
            'disclaimer': 'Performance data is simulated for demonstration purposes. Real performance data should be verified with official fund sources.'
        }
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON input'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'An unexpected error occurred: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "fund_performance_search",
    "description": "Search for mutual funds and ETFs by name, ticker, or asset class and retrieve their historical performance metrics including NAV, return rates, expense ratios, and risk ratings over configurable time periods. Returns matching funds with key performance indicators for investment research.",
    "category": "search",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search term for fund name, ticker symbol, or asset class keyword"
        },
        "search_type": {
            "type": "string",
            "description": "Type of search to perform: name search, ticker lookup, or asset class filter",
            "enum": [
                "name",
                "ticker",
                "asset_class"
            ]
        },
        "asset_class": {
            "type": "string",
            "description": "Optional: Filter by asset class (e.g., equity, bond, money market, hybrid). Only used when search_type is 'asset_class'."
        },
        "time_period": {
            "type": "string",
            "description": "Optional: Return metrics for this time period only (1M, 3M, YTD, 1Y, 3Y, 5Y). Defaults to 1Y if not specified.",
            "enum": [
                "1M",
                "3M",
                "YTD",
                "1Y",
                "3Y",
                "5Y"
            ]
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (1-50). Defaults to 10.",
            "minimum": 1,
            "maximum": 50
        }
    },
    "required": [
        "query",
        "search_type"
    ]
},
}
