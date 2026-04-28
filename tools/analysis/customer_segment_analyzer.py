"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    import math

    try:
        data = json.loads(payload)
        transactions = data.get('transactions', [])
        if not transactions:
            return json.dumps({'error': 'No transactions provided'})

        # Parse analysis date
        if 'analysis_date' in data and data['analysis_date']:
            try:
                analysis_date = datetime.strptime(data['analysis_date'], '%Y-%m-%d')
            except:
                return json.dumps({'error': 'Invalid analysis_date format, use YYYY-MM-DD'})
        else:
            analysis_date = datetime.now()

        # Group transactions by customer
        customer_data = {}
        for t in transactions:
            cid = t.get('customer_id')
            date_str = t.get('purchase_date')
            amount = t.get('amount')
            if not cid or not date_str or amount is None:
                continue
            try:
                purchase_date = datetime.strptime(date_str, '%Y-%m-%d')
            except:
                continue
            if cid not in customer_data:
                customer_data[cid] = []
            customer_data[cid].append({'date': purchase_date, 'amount': amount})

        if not customer_data:
            return json.dumps({'error': 'No valid customer data found'})

        # Calculate RFM metrics per customer
        rfm = {}
        for cid, purchases in customer_data.items():
            # Recency: days since last purchase
            last_date = max(p['date'] for p in purchases)
            recency = (analysis_date - last_date).days
            if recency < 0:
                recency = 0
            # Frequency: total number of purchases
            frequency = len(purchases)
            # Monetary: total amount spent
            monetary = sum(p['amount'] for p in purchases)
            rfm[cid] = {'recency': recency, 'frequency': frequency, 'monetary': monetary}

        # Normalize scores (1-5 scale using quintiles)
        def score(values, reverse=False):
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            quintiles = []
            for i in range(1, 5):
                idx = int(i * n / 5)
                if idx >= n:
                    idx = n - 1
                quintiles.append(sorted_vals[idx])
            scores = {}
            for cid, val in values.items():
                if reverse:
                    val = -val
                if val <= quintiles[0]:
                    scores[cid] = 1
                elif val <= quintiles[1]:
                    scores[cid] = 2
                elif val <= quintiles[2]:
                    scores[cid] = 3
                elif val <= quintiles[3]:
                    scores[cid] = 4
                else:
                    scores[cid] = 5
            return scores

        recency_scores = score({cid: v['recency'] for cid, v in rfm.items()}, reverse=True)
        frequency_scores = score({cid: v['frequency'] for cid, v in rfm.items()})
        monetary_scores = score({cid: v['monetary'] for cid, v in rfm.items()})

        # Assign segments based on RFM score combinations
        segment_names = {
            (5,5,5): 'Champions',
            (4,5,5): 'Champions',
            (5,4,5): 'Champions',
            (5,5,4): 'Champions',
            (4,4,5): 'Loyal Customers',
            (4,5,4): 'Loyal Customers',
            (5,4,4): 'Loyal Customers',
            (4,4,4): 'Loyal Customers',
            (3,5,5): 'Potential Loyalists',
            (3,4,5): 'Potential Loyalists',
            (3,5,4): 'Potential Loyalists',
            (3,4,4): 'Potential Loyalists',
            (4,3,5): 'New Customers',
            (4,3,4): 'New Customers',
            (5,3,5): 'New Customers',
            (5,3,4): 'New Customers',
            (3,3,5): 'Promising',
            (3,3,4): 'Promising',
            (2,5,5): 'At Risk',
            (2,4,5): 'At Risk',
            (2,5,4): 'At Risk',
            (2,4,4): 'At Risk',
            (1,5,5): 'Cannot Lose Them',
            (1,4,5): 'Cannot Lose Them',
            (1,5,4): 'Cannot Lose Them',
            (1,4,4): 'Cannot Lose Them',
            (1,3,5): 'Hibernating',
            (1,3,4): 'Hibernating',
            (2,3,5): 'Hibernating',
            (2,3,4): 'Hibernating',
            (1,2,5): 'Lost',
            (1,2,4): 'Lost',
            (1,1,5): 'Lost',
            (1,1,4): 'Lost',
        }
        default_segment = 'Others'

        recommendations = {
            'Champions': 'Reward with exclusive offers and VIP programs',
            'Loyal Customers': 'Upsell and cross-sell premium products',
            'Potential Loyalists': 'Offer membership or loyalty programs',
            'New Customers': 'Provide onboarding discounts and support',
            'Promising': 'Send targeted promotions to increase engagement',
            'At Risk': 'Run re-engagement campaigns with special discounts',
            'Cannot Lose Them': 'Personal outreach and win-back offers',
            'Hibernating': 'Send reactivation emails with limited-time deals',
            'Lost': 'Consider removing from active campaigns unless high value',
            'Others': 'General nurturing campaign'
        }

        result = []
        for cid in rfm:
            r_score = recency_scores[cid]
            f_score = frequency_scores[cid]
            m_score = monetary_scores[cid]
            key = (r_score, f_score, m_score)
            segment = segment_names.get(key, default_segment)
            rec = recommendations.get(segment, 'Standard engagement')
            result.append({
                'customer_id': cid,
                'recency_score': r_score,
                'frequency_score': f_score,
                'monetary_score': m_score,
                'segment': segment,
                'recommendation': rec
            })

        return json.dumps({'segments': result}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "customer_segment_analyzer",
    "description": "Analyze customer transaction data to identify distinct behavioral segments using recency, frequency, and monetary (RFM) scoring, and return segment labels (Champions, Loyal, At Risk, etc.) with actionable business recommendations for each group.",
    "category": "analysis",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "transactions": {
            "type": "array",
            "description": "List of customer transaction records, each containing customer_id, purchase_date (ISO 8601), and amount (positive number).",
            "items": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Unique identifier for the customer."
                    },
                    "purchase_date": {
                        "type": "string",
                        "description": "Date of purchase in YYYY-MM-DD format."
                    },
                    "amount": {
                        "type": "number",
                        "description": "Monetary value of the transaction, must be > 0."
                    }
                },
                "required": [
                    "customer_id",
                    "purchase_date",
                    "amount"
                ]
            }
        },
        "analysis_date": {
            "type": "string",
            "description": "Optional: Reference date for recency calculation in YYYY-MM-DD format. Defaults to current date if not provided."
        },
        "segment_count": {
            "type": "integer",
            "description": "Optional: Number of segments to generate (2 to 10). Default is 5 (standard RFM segments).",
            "minimum": 2,
            "maximum": 10
        }
    },
    "required": [
        "transactions"
    ]
},
}
