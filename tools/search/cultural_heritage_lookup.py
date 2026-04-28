"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        # Extract parameters with defaults
        country = data.get('country', '').strip().upper() if isinstance(data.get('country'), str) else ''
        category = data.get('category', '')
        name_query = data.get('name_query', '').strip() if isinstance(data.get('name_query'), str) else ''
        max_results = data.get('max_results', 10)
        if not isinstance(max_results, int) or max_results < 1:
            max_results = 10
        if max_results > 50:
            max_results = 50

        # Validate category if provided
        valid_categories = ['cultural', 'natural', 'mixed', '']
        if category not in valid_categories:
            return json.dumps({'error': 'Invalid category. Choose from cultural, natural, or mixed.'}, ensure_ascii=False)

        # Simulated database of heritage sites (in reality would query an API or database)
        sites = [
            {'name': 'Taj Mahal', 'country': 'IN', 'category': 'cultural', 'year': 1983, 'description': 'An ivory-white marble mausoleum on the right bank of the Yamuna river in Agra, built by Mughal emperor Shah Jahan.', 'location': {'lat': 27.1751, 'lon': 78.0421}},
            {'name': 'Great Wall of China', 'country': 'CN', 'category': 'cultural', 'year': 1987, 'description': 'A series of fortifications made of stone, brick, tamped earth, wood, and other materials, generally built along an east-to-west line across China.', 'location': {'lat': 40.4319, 'lon': 116.5704}},
            {'name': 'Galapagos Islands', 'country': 'EC', 'category': 'natural', 'year': 1978, 'description': 'An archipelago of volcanic islands in the Pacific Ocean, famous for unique wildlife that inspired Charles Darwin.', 'location': {'lat': -0.9538, 'lon': -90.9656}},
            {'name': 'Machu Picchu', 'country': 'PE', 'category': 'mixed', 'year': 1983, 'description': 'A 15th-century Inca citadel situated on a mountain ridge 2,430 metres above sea level in the Eastern Cordillera of southern Peru.', 'location': {'lat': -13.1631, 'lon': -72.5450}},
            {'name': 'Acropolis of Athens', 'country': 'GR', 'category': 'cultural', 'year': 1987, 'description': 'An ancient citadel located on a rocky outcrop above the city of Athens, containing the remains of several ancient buildings of great architectural and historic significance.', 'location': {'lat': 37.9715, 'lon': 23.7267}},
            {'name': 'Great Barrier Reef', 'country': 'AU', 'category': 'natural', 'year': 1981, 'description': 'The world\'s largest coral reef system composed of over 2,900 individual reefs and 900 islands stretching for over 2,300 kilometres.', 'location': {'lat': -18.2871, 'lon': 147.6992}},
            {'name': 'Pyramids of Giza', 'country': 'EG', 'category': 'cultural', 'year': 1979, 'description': 'Ancient Egyptian pyramid complex including the Great Pyramid of Giza, the Pyramid of Khafre, and the Pyramid of Menkaure.', 'location': {'lat': 29.9792, 'lon': 31.1342}},
            {'name': 'Yellowstone National Park', 'country': 'US', 'category': 'natural', 'year': 1978, 'description': 'A national park in the western US, largely in Wyoming, known for its geothermal features and diverse wildlife.', 'location': {'lat': 44.4280, 'lon': -110.5885}},
            {'name': 'Historic Monuments of Kyoto', 'country': 'JP', 'category': 'cultural', 'year': 1994, 'description': 'A collection of 17 locations in Kyoto, Uji, and Otsu in Japan, including temples, shrines, and gardens.', 'location': {'lat': 35.0116, 'lon': 135.7681}},
            {'name': 'Stonehenge', 'country': 'GB', 'category': 'cultural', 'year': 1986, 'description': 'A prehistoric monument in Wiltshire, England, consisting of a ring of standing stones set within earthworks.', 'location': {'lat': 51.1789, 'lon': -1.8262}},
            {'name': 'Amazon Rainforest', 'country': 'BR', 'category': 'natural', 'year': 2000, 'description': 'A moist broadleaf tropical rainforest in the Amazon biome that covers most of the Amazon basin of South America.', 'location': {'lat': -3.4653, 'lon': -62.2159}},
            {'name': 'Angkor Wat', 'country': 'KH', 'category': 'cultural', 'year': 1992, 'description': 'A vast Hindu-Buddhist temple complex in Cambodia, originally constructed as a Hindu temple dedicated to Lord Vishnu.', 'location': {'lat': 13.4125, 'lon': 103.8670}}
        ]

        # Filter by country if provided
        if country:
            sites = [s for s in sites if s['country'] == country]

        # Filter by category if provided
        if category:
            sites = [s for s in sites if s['category'] == category]

        # Filter by name query if provided
        if name_query:
            lower_query = name_query.lower()
            sites = [s for s in sites if lower_query in s['name'].lower()]

        # Sort by year descending for relevance
        sites.sort(key=lambda x: x['year'], reverse=True)

        # Limit results
        sites = sites[:max_results]

        # Format results
        result_list = []
        for site in sites:
            result_list.append({
                'name': site['name'],
                'country': site['country'],
                'category': site['category'],
                'year_inscribed': site['year'],
                'description': site['description'],
                'location': site['location']
            })

        response = {
            'count': len(result_list),
            'results': result_list
        }
        return json.dumps(response, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': f'An error occurred: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "cultural_heritage_lookup",
    "description": "Search the UNESCO World Heritage List by country, category, or name fragment and return matching site names, descriptions, year of inscription, and location details for educational or travel planning purposes.",
    "category": "search",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "country": {
            "type": "string",
            "description": "ISO 3166-1 alpha-2 country code to filter heritage sites by nation (e.g., FR, JP, IT)",
            "examples": [
                "US",
                "IN",
                "EG"
            ]
        },
        "category": {
            "type": "string",
            "enum": [
                "cultural",
                "natural",
                "mixed"
            ],
            "description": "Optional: filter by heritage category (cultural, natural, or mixed). If omitted, all categories are searched"
        },
        "name_query": {
            "type": "string",
            "description": "Optional: partial or full name of a heritage site to search for (case-insensitive, substring match)",
            "examples": [
                "Taj Mahal",
                "Great Barrier"
            ]
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: maximum number of matching sites to return (1-50, default 10)",
            "minimum": 1,
            "maximum": 50,
            "default": 10
        }
    },
    "required": []
},
}
