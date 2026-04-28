"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        customers = data.get('customers')
        strategy = data.get('segment_strategy')
        if not customers or not strategy:
            return json.dumps({"error": "Missing required fields: customers and segment_strategy"})
        
        segments = []
        if strategy == 'loyalty':
            # RFM-like segmentation based on recency, frequency, monetary
            scores = []
            for c in customers:
                recency_days = (datetime.now() - datetime.strptime(c['last_purchase_date'], '%Y-%m-%d')).days
                r_score = max(0, 10 - int(recency_days / 30))  # higher recency = lower score
                f_score = min(10, c['purchase_frequency'])
                m_score = min(10, int(c['total_spent'] / 100))
                total = r_score + f_score + m_score
                scores.append((c['id'], total, c))
            
            scores.sort(key=lambda x: x[1], reverse=True)
            top = [s[2] for s in scores[:max(1, len(scores)//3)]]
            mid = [s[2] for s in scores[len(scores)//3: 2*len(scores)//3]]
            low = [s[2] for s in scores[2*len(scores)//3:]]
            
            segments = [
                {"name": "Loyal Champions", "customer_ids": [c['id'] for c in top], "description": "Highest RFM score customers, frequent and recent buyers with high spend.", "suggested_strategy": "VIP rewards program, exclusive offers, referral incentives."},
                {"name": "Potential Loyalists", "customer_ids": [c['id'] for c in mid], "description": "Moderate RFM score, good engagement but room for growth.", "suggested_strategy": "Targeted upsell campaigns, loyalty program enrollment."},
                {"name": "At Risk", "customer_ids": [c['id'] for c in low], "description": "Low RFM score, low purchase frequency or long time since last purchase.", "suggested_strategy": "Re-engagement offers, win-back discounts, personalized recommendations."}
            ]
        elif strategy == 'churn_risk':
            now = datetime.now()
            high_risk = []
            medium_risk = []
            low_risk = []
            for c in customers:
                days_since_last = (now - datetime.strptime(c['last_purchase_date'], '%Y-%m-%d')).days
                freq = c['purchase_frequency']
                if days_since_last > 180 and freq < 2:
                    high_risk.append(c)
                elif days_since_last > 90 or freq < 5:
                    medium_risk.append(c)
                else:
                    low_risk.append(c)
            
            segments = [
                {"name": "High Churn Risk", "customer_ids": [c['id'] for c in high_risk], "description": "No purchase in 6+ months and low frequency.", "suggested_strategy": "Urgent re-engagement, limited-time offer, personal call."},
                {"name": "Medium Churn Risk", "customer_ids": [c['id'] for c in medium_risk], "description": "Some inactivity or low purchase frequency.", "suggested_strategy": "Email drip campaign, product recommendations based on past purchases."},
                {"name": "Low Churn Risk", "customer_ids": [c['id'] for c in low_risk], "description": "Active and frequent buyers.", "suggested_strategy": "Maintain engagement, offer loyalty bonuses."}
            ]
        elif strategy == 'high_value':
            sorted_customers = sorted(customers, key=lambda x: x['total_spent'], reverse=True)
            n = len(sorted_customers)
            top = sorted_customers[:max(1, n//3)]
            middle = sorted_customers[n//3: 2*n//3] if n >= 3 else []
            bottom = sorted_customers[2*n//3:] if n >= 3 else sorted_customers
            
            segments = [
                {"name": "High Spenders", "customer_ids": [c['id'] for c in top], "description": "Top third by total spend.", "suggested_strategy": "Premium support, early access to products, loyalty points."},
                {"name": "Medium Spenders", "customer_ids": [c['id'] for c in middle], "description": "Middle third by total spend.", "suggested_strategy": "Bundle deals, cross-selling, loyalty program."},
                {"name": "Low Spenders", "customer_ids": [c['id'] for c in bottom], "description": "Bottom third by total spend.", "suggested_strategy": "Discounts, free shipping thresholds, educational content."}
            ]
        elif strategy == 'geographic':
            from collections import defaultdict
            geo_groups = defaultdict(list)
            for c in customers:
                geo_groups[c['location']].append(c)
            
            for location, group in geo_groups.items():
                avg_spend = sum(c['total_spent'] for c in group) / len(group) if group else 0
                segments.append({
                    "name": f"{location} Cluster",
                    "customer_ids": [c['id'] for c in group],
                    "description": f"Customers from {location}, average spend ${avg_spend:.2f}.",
                    "suggested_strategy": f"Localized promotions, regional events, location-based ads for {location}."
                })
        elif strategy == 'demographic':
            from collections import defaultdict
            demo_groups = defaultdict(list)
            for c in customers:
                demo_groups[c['age_group']].append(c)
            
            for age, group in demo_groups.items():
                avg_engagement = sum(c['engagement_score'] for c in group) / len(group) if group else 0
                segments.append({
                    "name": f"Age Group {age}",
                    "customer_ids": [c['id'] for c in group],
                    "description": f"Customers aged {age}, average engagement score {avg_engagement:.1f}.",
                    "suggested_strategy": f"Age-appropriate marketing channels, product lines targeting {age} demographics."
                })
        else:
            return json.dumps({"error": f"Unknown segment_strategy: {strategy}. Valid options: loyalty, churn_risk, high_value, geographic, demographic."})
        
        if not segments:
            return json.dumps({"error": "No segments could be generated from the provided data."})
        
        return json.dumps({"segments": segments, "total_customers_processed": len(customers), "strategy_used": strategy}, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return f'error: Invalid JSON input - {e}'
    except KeyError as e:
        return f'error: Missing required field in customer record - {e}'
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "generate_customer_segments",
    "description": "Generates customer segments from a list of customer records based on purchase behavior, demographics, and engagement metrics. Returns a list of segments with descriptions and suggested marketing strategies for each segment.",
    "category": "operations",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "customers": {
            "type": "array",
            "description": "Array of customer objects, each containing id, age_group, location, total_spent, purchase_frequency, last_purchase_date, and engagement_score.",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique identifier for the customer (e.g., cust_123)."
                    },
                    "age_group": {
                        "type": "string",
                        "enum": [
                            "18-25",
                            "26-35",
                            "36-45",
                            "46-55",
                            "56+"
                        ],
                        "description": "Age group of the customer."
                    },
                    "location": {
                        "type": "string",
                        "description": "Geographic location (city or region) of the customer."
                    },
                    "total_spent": {
                        "type": "number",
                        "description": "Total amount spent by the customer in the current fiscal year (in USD)."
                    },
                    "purchase_frequency": {
                        "type": "integer",
                        "description": "Number of purchases made by the customer in the last 12 months."
                    },
                    "last_purchase_date": {
                        "type": "string",
                        "description": "Date of the most recent purchase (format: YYYY-MM-DD)."
                    },
                    "engagement_score": {
                        "type": "number",
                        "description": "Engagement score from 0 to 100, based on email opens, website visits, and support interactions."
                    }
                },
                "required": [
                    "id",
                    "age_group",
                    "location",
                    "total_spent",
                    "purchase_frequency",
                    "last_purchase_date",
                    "engagement_score"
                ]
            },
            "minItems": 1
        },
        "segment_strategy": {
            "type": "string",
            "enum": [
                "loyalty",
                "churn_risk",
                "high_value",
                "geographic",
                "demographic"
            ],
            "description": "The strategy used to define segments. 'loyalty': based on RFM scoring; 'churn_risk': based on recency and frequency; 'high_value': based on total_spent; 'geographic': based on location clusters; 'demographic': based on age_group."
        }
    },
    "required": [
        "customers",
        "segment_strategy"
    ]
},
}
