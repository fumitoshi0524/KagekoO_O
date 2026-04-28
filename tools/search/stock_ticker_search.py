"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for stock ticker symbols and company information using partial company names, sectors, or keywords."""
    import json
    try:
        data = json.loads(payload)
        query = data.get('query', '').strip().lower()
        if not query or len(query) < 2:
            return json.dumps({'error': 'Query must be at least 2 characters'}, ensure_ascii=False)
        
        exchange_filter = data.get('exchange', None)
        limit = min(max(int(data.get('limit', 10)), 1), 50)
        include_details = data.get('include_details', False)
        
        # Comprehensive stock database with real ticker information
        stock_database = [
            {'ticker': 'AAPL', 'name': 'Apple Inc.', 'exchange': 'XNAS', 'sector': 'Technology', 'industry': 'Consumer Electronics', 'market_cap': '3.0T'},
            {'ticker': 'MSFT', 'name': 'Microsoft Corporation', 'exchange': 'XNAS', 'sector': 'Technology', 'industry': 'Software—Infrastructure', 'market_cap': '2.8T'},
            {'ticker': 'GOOGL', 'name': 'Alphabet Inc.', 'exchange': 'XNAS', 'sector': 'Communication Services', 'industry': 'Internet Content & Information', 'market_cap': '1.8T'},
            {'ticker': 'AMZN', 'name': 'Amazon.com Inc.', 'exchange': 'XNAS', 'sector': 'Consumer Cyclical', 'industry': 'Internet Retail', 'market_cap': '1.9T'},
            {'ticker': 'NVDA', 'name': 'NVIDIA Corporation', 'exchange': 'XNAS', 'sector': 'Technology', 'industry': 'Semiconductors', 'market_cap': '2.2T'},
            {'ticker': 'META', 'name': 'Meta Platforms Inc.', 'exchange': 'XNAS', 'sector': 'Communication Services', 'industry': 'Internet Content & Information', 'market_cap': '1.2T'},
            {'ticker': 'TSLA', 'name': 'Tesla Inc.', 'exchange': 'XNAS', 'sector': 'Consumer Cyclical', 'industry': 'Auto Manufacturers', 'market_cap': '0.6T'},
            {'ticker': 'BRK.B', 'name': 'Berkshire Hathaway Inc.', 'exchange': 'XNYS', 'sector': 'Financial Services', 'industry': 'Insurance—Diversified', 'market_cap': '0.9T'},
            {'ticker': 'JPM', 'name': 'JPMorgan Chase & Co.', 'exchange': 'XNYS', 'sector': 'Financial Services', 'industry': 'Banks—Diversified', 'market_cap': '0.5T'},
            {'ticker': 'V', 'name': 'Visa Inc.', 'exchange': 'XNYS', 'sector': 'Financial Services', 'industry': 'Credit Services', 'market_cap': '0.5T'},
            {'ticker': 'JNJ', 'name': 'Johnson & Johnson', 'exchange': 'XNYS', 'sector': 'Healthcare', 'industry': 'Drug Manufacturers—General', 'market_cap': '0.4T'},
            {'ticker': 'WMT', 'name': 'Walmart Inc.', 'exchange': 'XNYS', 'sector': 'Consumer Defensive', 'industry': 'Discount Stores', 'market_cap': '0.5T'},
            {'ticker': 'PG', 'name': 'Procter & Gamble Company', 'exchange': 'XNYS', 'sector': 'Consumer Defensive', 'industry': 'Household & Personal Products', 'market_cap': '0.4T'},
            {'ticker': 'MA', 'name': 'Mastercard Incorporated', 'exchange': 'XNYS', 'sector': 'Financial Services', 'industry': 'Credit Services', 'market_cap': '0.4T'},
            {'ticker': 'UNH', 'name': 'UnitedHealth Group Incorporated', 'exchange': 'XNYS', 'sector': 'Healthcare', 'industry': 'Healthcare Plans', 'market_cap': '0.5T'},
            {'ticker': 'HD', 'name': 'The Home Depot Inc.', 'exchange': 'XNYS', 'sector': 'Consumer Cyclical', 'industry': 'Home Improvement Retail', 'market_cap': '0.3T'},
            {'ticker': 'DIS', 'name': 'The Walt Disney Company', 'exchange': 'XNYS', 'sector': 'Communication Services', 'industry': 'Entertainment', 'market_cap': '0.2T'},
            {'ticker': 'BAC', 'name': 'Bank of America Corporation', 'exchange': 'XNYS', 'sector': 'Financial Services', 'industry': 'Banks—Diversified', 'market_cap': '0.3T'},
            {'ticker': 'NFLX', 'name': 'Netflix Inc.', 'exchange': 'XNAS', 'sector': 'Communication Services', 'industry': 'Entertainment', 'market_cap': '0.2T'},
            {'ticker': 'ADBE', 'name': 'Adobe Inc.', 'exchange': 'XNAS', 'sector': 'Technology', 'industry': 'Software—Infrastructure', 'market_cap': '0.2T'},
            {'ticker': 'CRM', 'name': 'Salesforce Inc.', 'exchange': 'XNYS', 'sector': 'Technology', 'industry': 'Software—Application', 'market_cap': '0.3T'},
            {'ticker': 'INTC', 'name': 'Intel Corporation', 'exchange': 'XNAS', 'sector': 'Technology', 'industry': 'Semiconductors', 'market_cap': '0.1T'},
            {'ticker': 'CSCO', 'name': 'Cisco Systems Inc.', 'exchange': 'XNAS', 'sector': 'Technology', 'industry': 'Communication Equipment', 'market_cap': '0.2T'},
            {'ticker': 'PEP', 'name': 'PepsiCo Inc.', 'exchange': 'XNAS', 'sector': 'Consumer Defensive', 'industry': 'Beverages—Non-Alcoholic', 'market_cap': '0.2T'},
            {'ticker': 'KO', 'name': 'The Coca-Cola Company', 'exchange': 'XNYS', 'sector': 'Consumer Defensive', 'industry': 'Beverages—Non-Alcoholic', 'market_cap': '0.3T'},
            {'ticker': 'ABBV', 'name': 'AbbVie Inc.', 'exchange': 'XNYS', 'sector': 'Healthcare', 'industry': 'Drug Manufacturers—General', 'market_cap': '0.3T'},
            {'ticker': 'AVGO', 'name': 'Broadcom Inc.', 'exchange': 'XNAS', 'sector': 'Technology', 'industry': 'Semiconductors', 'market_cap': '0.6T'},
            {'ticker': 'TMO', 'name': 'Thermo Fisher Scientific Inc.', 'exchange': 'XNYS', 'sector': 'Healthcare', 'industry': 'Diagnostics & Research', 'market_cap': '0.2T'},
            {'ticker': 'COST', 'name': 'Costco Wholesale Corporation', 'exchange': 'XNAS', 'sector': 'Consumer Defensive', 'industry': 'Discount Stores', 'market_cap': '0.3T'},
            {'ticker': 'DHR', 'name': 'Danaher Corporation', 'exchange': 'XNYS', 'sector': 'Healthcare', 'industry': 'Diagnostics & Research', 'market_cap': '0.2T'},
            {'ticker': 'TM', 'name': 'Toyota Motor Corporation', 'exchange': 'XNYS', 'sector': 'Consumer Cyclical', 'industry': 'Auto Manufacturers', 'market_cap': '0.3T'},
            {'ticker': 'HSBC', 'name': 'HSBC Holdings plc', 'exchange': 'XLON', 'sector': 'Financial Services', 'industry': 'Banks—Diversified', 'market_cap': '0.1T'},
            {'ticker': 'BABA', 'name': 'Alibaba Group Holding Limited', 'exchange': 'XNYS', 'sector': 'Consumer Cyclical', 'industry': 'Internet Retail', 'market_cap': '0.2T'},
            {'ticker': 'TSM', 'name': 'Taiwan Semiconductor Manufacturing Company Limited', 'exchange': 'XNYS', 'sector': 'Technology', 'industry': 'Semiconductors', 'market_cap': '0.7T'},
            {'ticker': 'NVS', 'name': 'Novartis AG', 'exchange': 'XNYS', 'sector': 'Healthcare', 'industry': 'Drug Manufacturers—General', 'market_cap': '0.2T'},
            {'ticker': 'SAP', 'name': 'SAP SE', 'exchange': 'XNYS', 'sector': 'Technology', 'industry': 'Software—Application', 'market_cap': '0.2T'},
            {'ticker': 'UL', 'name': 'Unilever PLC', 'exchange': 'XNYS', 'sector': 'Consumer Defensive', 'industry': 'Household & Personal Products', 'market_cap': '0.1T'},
            {'ticker': 'BP', 'name': 'BP p.l.c.', 'exchange': 'XNYS', 'sector': 'Energy', 'industry': 'Oil & Gas Integrated', 'market_cap': '0.1T'},
            {'ticker': 'SHEL', 'name': 'Shell plc', 'exchange': 'XNYS', 'sector': 'Energy', 'industry': 'Oil & Gas Integrated', 'market_cap': '0.2T'},
            {'ticker': 'RY', 'name': 'Royal Bank of Canada', 'exchange': 'XTSE', 'sector': 'Financial Services', 'industry': 'Banks—Diversified', 'market_cap': '0.1T'},
        ]
        
        results = []
        for stock in stock_database:
            # Search in ticker, name, sector, and industry
            if (query in stock['ticker'].lower() or 
                query in stock['name'].lower() or 
                (stock['sector'] and query in stock['sector'].lower()) or
                (stock.get('industry') and query in stock['industry'].lower())):
                
                # Apply exchange filter if specified
                if exchange_filter and stock['exchange'] != exchange_filter:
                    continue
                    
                result_item = {
                    'ticker': stock['ticker'],
                    'name': stock['name'],
                    'exchange': stock['exchange']
                }
                
                if include_details:
                    result_item['sector'] = stock.get('sector', '')
                    result_item['industry'] = stock.get('industry', '')
                    result_item['market_cap'] = stock.get('market_cap', '')
                
                results.append(result_item)
                
                if len(results) >= limit:
                    break
        
        return json.dumps({
            'query': data['query'],
            'total_matches': len(results),
            'results': results
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({'error': f'Search failed: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "stock_ticker_search",
    "description": "Search for stock ticker symbols and company information using partial company names, sectors, or keywords, returning matching tickers, exchange affiliations, and company descriptions.",
    "category": "search",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Company name, partial name, sector, or keyword to search for matching stock tickers (minimum 2 characters)",
            "minLength": 2,
            "maxLength": 200
        },
        "exchange": {
            "type": "string",
            "description": "Optional: Filter results to a specific stock exchange using ISO market identifier code (e.g., XNYS for NYSE, XNAS for Nasdaq, XLON for London Stock Exchange)",
            "enum": [
                "XNYS",
                "XNAS",
                "XLON",
                "XTKS",
                "XHKG",
                "XSHG",
                "XSHE",
                "XETR",
                "XPAR",
                "XTSE",
                "XASX",
                "XBOM",
                "XNSE"
            ]
        },
        "limit": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (1-50, default: 10)",
            "minimum": 1,
            "maximum": 50,
            "default": 10
        },
        "include_details": {
            "type": "boolean",
            "description": "Optional: Include additional company details such as sector, industry, and market cap range (default: False)",
            "default": False
        }
    },
    "required": [
        "query"
    ]
},
}
