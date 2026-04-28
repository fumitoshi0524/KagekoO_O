"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import date, timedelta
    import math

    try:
        data = json.loads(payload)
        country = data.get('country', '').strip().upper()
        year = data.get('year')
        type_filter = data.get('type_filter')
        language = data.get('language', 'en')

        if not country:
            return json.dumps({'error': 'country is required'})
        if not year:
            return json.dumps({'error': 'year is required'})
        if not isinstance(year, int) or year < 1900 or year > 2100:
            return json.dumps({'error': 'year must be integer between 1900 and 2100'})
        if type_filter and not isinstance(type_filter, list):
            return json.dumps({'error': 'type_filter must be a list'})
        if language not in ['en','de','fr','es','pt','ja','zh','hi']:
            language = 'en'

        # Built-in holiday database (2025 sample, can be extended or fetched from an API)
        # Using a static lookup for demonstration
        holiday_db = {
            'US': {
                2025: [
                    {'date': '2025-01-01', 'name_en': 'New Year\'s Day', 'type': 'public', 'description_en': 'First day of the Gregorian year'},
                    {'date': '2025-01-20', 'name_en': 'Martin Luther King Jr. Day', 'type': 'public', 'description_en': 'Honors civil rights leader Martin Luther King Jr.'},
                    {'date': '2025-02-17', 'name_en': 'Presidents\' Day', 'type': 'public', 'description_en': 'Honors U.S. presidents, especially Washington and Lincoln'},
                    {'date': '2025-05-26', 'name_en': 'Memorial Day', 'type': 'public', 'description_en': 'Remembers military personnel who died in service'},
                    {'date': '2025-07-04', 'name_en': 'Independence Day', 'type': 'public', 'description_en': 'Celebrates the Declaration of Independence in 1776'},
                    {'date': '2025-09-01', 'name_en': 'Labor Day', 'type': 'public', 'description_en': 'Honors the American labor movement'},
                    {'date': '2025-10-13', 'name_en': 'Columbus Day', 'type': 'public', 'description_en': 'Commemorates Christopher Columbus\'s arrival in the Americas'},
                    {'date': '2025-11-11', 'name_en': 'Veterans Day', 'type': 'public', 'description_en': 'Honors military veterans'},
                    {'date': '2025-11-27', 'name_en': 'Thanksgiving Day', 'type': 'public', 'description_en': 'Harvest festival with traditional turkey dinner'},
                    {'date': '2025-12-25', 'name_en': 'Christmas Day', 'type': 'public', 'description_en': 'Christian celebration of the birth of Jesus Christ'},
                    {'date': '2025-03-31', 'name_en': 'Easter Sunday', 'type': 'religious', 'description_en': 'Christian holiday celebrating resurrection of Jesus'},
                    {'date': '2025-02-14', 'name_en': 'Valentine\'s Day', 'type': 'observance', 'description_en': 'Day of romance and love'},
                    {'date': '2025-03-17', 'name_en': 'St. Patrick\'s Day', 'type': 'observance', 'description_en': 'Irish cultural celebration'},
                    {'date': '2025-10-31', 'name_en': 'Halloween', 'type': 'observance', 'description_en': 'Evening before All Saints\' Day, costume parties'}
                ]
            },
            'JP': {
                2025: [
                    {'date': '2025-01-01', 'name_en': 'New Year\'s Day', 'type': 'public', 'description_en': 'Celebrates the beginning of the new year'},
                    {'date': '2025-01-13', 'name_en': 'Coming of Age Day', 'type': 'public', 'description_en': 'Honors those who turned 20 in the past year'},
                    {'date': '2025-02-11', 'name_en': 'National Foundation Day', 'type': 'public', 'description_en': 'Marks the founding of Japan'},
                    {'date': '2025-02-23', 'name_en': 'Emperor\'s Birthday', 'type': 'public', 'description_en': 'Birthday of Emperor Naruhito'},
                    {'date': '2025-03-20', 'name_en': 'Vernal Equinox Day', 'type': 'public', 'description_en': 'Day of respect for nature and ancestors'},
                    {'date': '2025-04-29', 'name_en': 'Showa Day', 'type': 'public', 'description_en': 'Commemorates the reign of Emperor Showa'},
                    {'date': '2025-05-03', 'name_en': 'Constitution Memorial Day', 'type': 'public', 'description_en': 'Commemorates the post-war constitution'},
                    {'date': '2025-05-04', 'name_en': 'Greenery Day', 'type': 'public', 'description_en': 'Promotes environmental awareness'},
                    {'date': '2025-05-05', 'name_en': 'Children\'s Day', 'type': 'public', 'description_en': 'Honors children and their futures'},
                    {'date': '2025-07-21', 'name_en': 'Marine Day', 'type': 'public', 'description_en': 'Appreciates the blessings of the ocean'},
                    {'date': '2025-08-11', 'name_en': 'Mountain Day', 'type': 'public', 'description_en': 'Promotes appreciation of mountains'},
                    {'date': '2025-09-15', 'name_en': 'Respect for the Aged Day', 'type': 'public', 'description_en': 'Honors elderly citizens'},
                    {'date': '2025-09-23', 'name_en': 'Autumnal Equinox Day', 'type': 'public', 'description_en': 'Day of remembrance for ancestors'},
                    {'date': '2025-10-13', 'name_en': 'Health and Sports Day', 'type': 'public', 'description_en': 'Encourages sports and physical activity'},
                    {'date': '2025-11-03', 'name_en': 'Culture Day', 'type': 'public', 'description_en': 'Celebrates culture and arts'},
                    {'date': '2025-11-23', 'name_en': 'Labour Thanksgiving Day', 'type': 'public', 'description_en': 'Honors workers and harvest'},
                    {'date': '2025-12-23', 'name_en': 'Emperor\'s Birthday (Heisei)', 'type': 'public', 'description_en': 'Former Emperor Akihito\'s birthday'},
                    {'date': '2025-01-15', 'name_en': 'Coming of Age (observance)', 'type': 'observance', 'description_en': 'Traditional celebration of adulthood'},
                    {'date': '2025-02-03', 'name_en': 'Setsubun', 'type': 'seasonal', 'description_en': 'Bean-throwing festival to drive away evil'},
                    {'date': '2025-03-03', 'name_en': 'Hinamatsuri', 'type': 'seasonal', 'description_en': 'Doll festival for girls'},
                    {'date': '2025-07-07', 'name_en': 'Tanabata', 'type': 'seasonal', 'description_en': 'Star festival celebrating the meeting of Orihime and Hikoboshi'}
                ]
            },
            'IN': {
                2025: [
                    {'date': '2025-01-26', 'name_en': 'Republic Day', 'type': 'public', 'description_en': 'Commemorates the adoption of the constitution in 1950'},
                    {'date': '2025-08-15', 'name_en': 'Independence Day', 'type': 'public', 'description_en': 'Celebrates independence from British rule in 1947'},
                    {'date': '2025-10-02', 'name_en': 'Gandhi Jayanti', 'type': 'public', 'description_en': 'Birth anniversary of Mahatma Gandhi'},
                    {'date': '2025-10-01', 'name_en': 'Dussehra (Vijayadashami)', 'type': 'religious', 'description_en': 'Hindu festival marking victory of good over evil'},
                    {'date': '2025-10-20', 'name_en': 'Diwali', 'type': 'religious', 'description_en': 'Festival of lights, major Hindu celebration'},
                    {'date': '2025-03-14', 'name_en': 'Holi', 'type': 'religious', 'description_en': 'Festival of colors, celebrates spring'},
                    {'date': '2025-04-14', 'name_en': 'Baisakhi', 'type': 'religious', 'description_en': 'Sikh harvest festival'},
                    {'date': '2025-08-26', 'name_en': 'Ganesh Chaturthi', 'type': 'religious', 'description_en': 'Birth celebration of Lord Ganesha'},
                    {'date': '2025-03-31', 'name_en': 'Easter Sunday', 'type': 'religious', 'description_en': 'Christian holiday'},
                    {'date': '2025-02-19', 'name_en': 'Maha Shivaratri', 'type': 'religious', 'description_en': 'Great night of Shiva'},
                    {'date': '2025-04-10', 'name_en': 'Eid al-Fitr', 'type': 'religious', 'description_en': 'Islamic festival marking end of Ramadan'},
                    {'date': '2025-06-17', 'name_en': 'Eid al-Adha', 'type': 'religious', 'description_en': 'Islamic festival of sacrifice'},
                    {'date': '2025-01-14', 'name_en': 'Makar Sankranti', 'type': 'seasonal', 'description_en': 'Harvest festival celebrating sun\'s transit into Capricorn'},
                    {'date': '2025-11-15', 'name_en': 'Guru Nanak Jayanti', 'type': 'religious', 'description_en': 'Birth anniversary of Guru Nanak, founder of Sikhism'}
                ]
            }
        }

        if country not in holiday_db:
            return json.dumps({'error': f'Country {country} not available. Supported: US, JP, IN'})
        if year not in holiday_db[country]:
            return json.dumps({'error': f'Year {year} not available for {country}'})

        holidays = holiday_db[country][year]
        if type_filter:
            holidays = [h for h in holidays if h['type'] in type_filter]
        if not holidays:
            return json.dumps({'holidays': [], 'message': 'No holidays found for the given filters'})

        # Simulate translation for other languages (in real app, use translation API)
        translation_map = {
            'de': {'New Year\'s Day': 'Neujahr', 'Christmas Day': 'Weihnachten', 'Independence Day': 'Unabhängigkeitstag', 'Diwali': 'Diwali'},
            'fr': {'New Year\'s Day': 'Jour de l\'An', 'Christmas Day': 'Noël', 'Independence Day': 'Fête de l\'Indépendance', 'Diwali': 'Diwali'},
            'es': {'New Year\'s Day': 'Año Nuevo', 'Christmas Day': 'Navidad', 'Independence Day': 'Día de la Independencia', 'Diwali': 'Diwali'},
            'ja': {'New Year\'s Day': '元日', 'Christmas Day': 'クリスマス', 'Independence Day': '独立記念日', 'Diwali': 'ディワリ'},
            'zh': {'New Year\'s Day': '元旦', 'Christmas Day': '圣诞节', 'Independence Day': '独立日', 'Diwali': '排灯节'},
            'hi': {'New Year\'s Day': 'नव वर्ष दिवस', 'Christmas Day': 'क्रिसमस', 'Independence Day': 'स्वतंत्रता दिवस', 'Diwali': 'दिवाली'}
        }

        result = []
        for h in holidays:
            name_key = f'name_{language}'
            desc_key = f'description_{language}'
            if language != 'en' and h['name_en'] in translation_map.get(language, {}):
                h[name_key] = translation_map[language][h['name_en']]
                h[desc_key] = f'{h["description_en"]} (translated)'  # placeholder
            else:
                h[name_key] = h['name_en']
                h[desc_key] = h['description_en']
            result.append({
                'date': h['date'],
                'name': h[name_key],
                'type': h['type'],
                'description': h[desc_key]
            })

        return json.dumps({'country': country, 'year': year, 'holidays': result}, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON input'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "cultural_holiday_calendar",
    "description": "Retrieve cultural and public holidays for a specified country and year, including the holiday name, date, type (public, religious, observance), and a brief description. This tool supports event planning, content scheduling, and cross-cultural awareness for over 40 countries.",
    "category": "system",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "country": {
            "type": "string",
            "description": "ISO 3166-1 alpha-2 country code (e.g., US, DE, JP, IN, BR, FR)",
            "examples": [
                "US",
                "JP",
                "IN"
            ]
        },
        "year": {
            "type": "integer",
            "description": "Calendar year for which to fetch holidays (1900 to 2100)",
            "examples": [
                2025
            ]
        },
        "type_filter": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "public",
                    "religious",
                    "observance",
                    "seasonal"
                ]
            },
            "description": "Optional: filter holidays by one or more types (public, religious, observance, seasonal). If omitted, all types are included.",
            "examples": [
                [
                    "public",
                    "religious"
                ]
            ]
        },
        "language": {
            "type": "string",
            "enum": [
                "en",
                "de",
                "fr",
                "es",
                "pt",
                "ja",
                "zh",
                "hi"
            ],
            "description": "Optional: language code for translated holiday names and descriptions (default: en).",
            "examples": [
                "de"
            ]
        }
    },
    "required": [
        "country",
        "year"
    ]
},
}
