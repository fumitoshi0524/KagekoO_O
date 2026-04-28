"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Translate idioms, proverbs, and culturally specific expressions from a source language to a target language, returning the literal meaning, equivalent expression, and cultural context notes to help users understand the original nuance and use the translation appropriately."""
    import json

    try:
        data = json.loads(payload)
        source_lang = data.get('source_language')
        target_lang = data.get('target_language')
        expression = data.get('expression')
        formality = data.get('formality_level', 'any')

        if not source_lang or not target_lang or not expression:
            return json.dumps({'error': 'source_language, target_language, and expression are required'}, ensure_ascii=False)

        # Comprehensive dictionary of idioms and expressions across cultures
        expression_db = {
            # English idioms
            ('en', 'fr', 'break the ice'): {
                'literal_meaning': 'Briser la glace',
                'equivalent_expression': 'Briser la glace',
                'culture_notes': 'This expression exists in both languages with the same meaning of initiating conversation to reduce tension. In French, it is used in identical social contexts—meetings, first dates, or networking events.',
                'formality': 'neutral'
            },
            ('en', 'es', 'break the ice'): {
                'literal_meaning': 'Romper el hielo',
                'equivalent_expression': 'Romper el hielo',
                'culture_notes': 'Direct equivalent used in Spanish-speaking cultures. Commonly used in both personal and professional settings throughout Latin America and Spain.',
                'formality': 'neutral'
            },
            ('en', 'ja', 'break the ice'): {
                'literal_meaning': 'Kōri o waru (氷を割る)',
                'equivalent_expression': 'Kūki o yomu (空気を読む) or Sekkin suru (接近する)',
                'culture_notes': 'Japanese culture places high value on group harmony (wa). Instead of directly 'breaking the ice', Japanese speakers might use indirect approaches like 'reading the air' or gradually approaching a topic. Direct equivalents exist but are less common.',
                'formality': 'informal'
            },
            ('fr', 'en', 'c\'est la fin des haricots'): {
                'literal_meaning': 'It\'s the end of the beans',
                'equivalent_expression': 'It\'s the last straw / It\'s game over',
                'culture_notes': 'This 19th-century French expression refers to beans being a cheap staple food; when the beans run out, the situation is dire. Use in dramatic, humorous, or exasperated contexts.',
                'formality': 'informal'
            },
            ('es', 'en', 'dar en el clavo'): {
                'literal_meaning': 'To hit the nail',
                'equivalent_expression': 'To hit the nail on the head',
                'culture_notes': 'Nearly identical meaning and usage across Spanish and English. Used when someone makes a perfectly accurate observation or achieves a precise result.',
                'formality': 'neutral'
            },
            ('ja', 'en', '猫の手も借りたい'): {
                'literal_meaning': 'One would even borrow a cat\'s hands',
                'equivalent_expression': 'Extremely busy / Up to one\'s ears in work',
                'culture_notes': 'This Japanese expression conveys that one is so busy they would accept help from the most unhelpful source—a cat, which does not have opposable thumbs. It conveys frantic busyness with a touch of humor.',
                'formality': 'informal'
            },
            ('ar', 'en', 'على قد لحافك مد رجليك'): {
                'literal_meaning': 'Stretch your legs as far as your blanket reaches',
                'equivalent_expression': 'Cut your coat according to your cloth',
                'culture_notes': 'Common Arabic proverb advising people to live within their means. Used across the Arab world from Morocco to the Gulf, with slight dialectal variations. It reflects practical wisdom in resource management.',
                'formality': 'formal'
            },
            ('zh', 'en', '画蛇添足'): {
                'literal_meaning': 'Draw legs on a snake',
                'equivalent_expression': 'Gild the lily / Ruin something by overdoing it',
                'culture_notes': 'From an ancient Chinese fable about a man who lost a contest by adding legs to his drawing of a snake. Teaches the lesson that unnecessary additions can spoil a perfectly finished thing. Used in both business and everyday contexts.',
                'formality': 'formal'
            },
            ('de', 'en', 'Tomaten auf den Augen haben'): {
                'literal_meaning': 'To have tomatoes on one\'s eyes',
                'equivalent_expression': 'To be blind to something obvious / Can\'t see what\'s right in front of you',
                'culture_notes': 'This German idiom is used humorously when someone fails to notice something that is clearly visible. It is similar to the English 'to have blinkers on' but more whimsical. Popular in both formal and casual German speech.',
                'formality': 'informal'
            },
            ('it', 'en', 'Non tutte le ciambelle riescono col buco'): {
                'literal_meaning': 'Not all donuts come out with a hole',
                'equivalent_expression': 'Not everything goes according to plan / Things don\'t always work out',
                'culture_notes': 'A light-hearted Italian expression used to console someone when things go wrong. The imagery comes from traditional Italian donuts (ciambelle), which sometimes bake without a hole when the dough expands imperfectly. Very common in casual conversation.',
                'formality': 'informal'
            },
            ('pt', 'en', 'Quem não tem cão, caça com gato'): {
                'literal_meaning': 'He who has no dog, hunts with a cat',
                'equivalent_expression': 'Make do with what you have / Use an alternative when the preferred option is unavailable',
                'culture_notes': 'Popular in both Portugal and Brazil, this expression emphasizes resourcefulness and creativity when ideal tools or resources are unavailable. Use in everyday conversation.',
                'formality': 'informal'
            },
            ('ko', 'en', '가는 말이 고와야 오는 말이 곱다'): {
                'literal_meaning': 'If the outgoing words are nice, the incoming words will be nice',
                'equivalent_expression': 'What goes around comes around / A soft answer turns away wrath',
                'culture_notes': 'Core Korean cultural value emphasizing reciprocal politeness and respect. Central to Korean communication norms. Used to remind someone to speak kindly to receive kindness in return.',
                'formality': 'formal'
            },
            ('ru', 'en', 'Без труда не выловишь и рыбку из пруда'): {
                'literal_meaning': 'You cannot even pull a fish out of the pond without effort',
                'equivalent_expression': 'No pain, no gain / Nothing worth having comes easy',
                'culture_notes': 'A classic Russian proverb reflecting the cultural appreciation for hard work and perseverance. Often said to encourage someone facing difficult tasks. The imagery of fishing is deeply rooted in Russian rural life.',
                'formality': 'formal'
            },
            ('th', 'en', 'ปลาหมอตายเพราะปาก'): {
                'literal_meaning': 'The fighting fish dies because of its mouth',
                'equivalent_expression': 'He who talks too much brings trouble upon himself / The pen is mightier than the sword (ironic twist)',
                'culture_notes': 'Thai proverb warning about careless speech. The fighting fish (pla moh) is known for its aggressive behavior; in the Thai context, it symbolizes how one\'s own words can cause self-destruction. Used to advise caution in communication.',
                'formality': 'formal'
            },
            ('hi', 'en', 'नाच न जाने आंगन टेढ़ा'): {
                'literal_meaning': 'If you do not know how to dance, you blame the courtyard',
                'equivalent_expression': 'A bad workman blames his tools / When you can\'t dance, you say the floor is crooked',
                'culture_notes': 'Common Hindi proverb used in both Hindi and Urdu-speaking regions. Points out the human tendency to blame external factors instead of accepting personal lack of skill. The courtyard (aangan) is a traditional open space in Indian homes used for gatherings and activities.',
                'formality': 'informal'
            },
            ('nl', 'en', 'Haastige spoed is zelden goed'): {
                'literal_meaning': 'Hasty speed is seldom good',
                'equivalent_expression': 'Haste makes waste / More haste, less speed',
                'culture_notes': 'Dutch proverb emphasizing carefulness over rushing. Reflects the Dutch cultural values of precision, planning, and caution. Commonly used in both work environments and personal contexts.',
                'formality': 'formal'
            },
            ('tr', 'en', 'Damlaya damlaya göl olur'): {
                'literal_meaning': 'Drop by drop, a lake forms',
                'equivalent_expression': 'Little strokes fell great oaks / Every little bit helps',
                'culture_notes': 'Turkish proverb emphasizing the power of small, consistent efforts over time. Used in contexts of saving money, learning skills, or making gradual improvements. The proverb reflects the Anatolian landscape where water accumulation is crucial.',
                'formality': 'formal'
            }
        }

        # Check for exact match in database
        key = (source_lang, target_lang, expression)
        if key in expression_db:
            result = expression_db[key]
            # Filter by formality if specified
            if formality != 'any' and result['formality'] != formality:
                # Return the result anyway with a note about formality mismatch
                result['formality_note'] = f"Note: The requested formality level '{formality}' does not match the expression's natural formality level '{result['formality']}'. The closest equivalent for your context is still provided."
            return json.dumps({
                'source_expression': expression,
                'source_language': source_lang,
                'target_language': target_lang,
                'literal_meaning': result['literal_meaning'],
                'equivalent_expression': result['equivalent_expression'],
                'culture_notes': result['culture_notes'],
                'formality_level': result['formality']
            }, ensure_ascii=False)
        else:
            # For expressions not in the database, return a best-effort translation
            return json.dumps({
                'source_expression': expression,
                'source_language': source_lang,
                'target_language': target_lang,
                'literal_meaning': f'[Machine-generated literal translation] The phrase "{expression}" does not have an exact idiomatic match in the current database. It may be best translated literally or rephrased for context.',
                'equivalent_expression': f'[No direct equivalent found] This expression appears to be culturally specific and may not have a natural equivalent in the target language. Consider providing more context or using a simpler rephrasing.',
                'culture_notes': f'This expression was not found in our cultural expressions database for {source_lang} to {target_lang} translation. The database covers common idioms and proverbs across 15 languages. You may repeat the query in a different language pair or check the spelling of the expression.',
                'formality_level': 'unknown'
            }, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error during translation: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "translate_cultural_expression",
    "description": "Translate idioms, proverbs, and culturally specific expressions from a source language to a target language, returning the literal meaning, equivalent expression, and cultural context notes to help users understand the original nuance and use the translation appropriately.",
    "category": "operations",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "source_language": {
            "type": "string",
            "description": "The language of the input expression, specified as a two-letter ISO 639-1 code (e.g., 'en', 'fr', 'ja')",
            "enum": [
                "en",
                "fr",
                "es",
                "de",
                "it",
                "pt",
                "nl",
                "ru",
                "ar",
                "zh",
                "ja",
                "ko",
                "th",
                "hi",
                "tr"
            ]
        },
        "target_language": {
            "type": "string",
            "description": "The language to translate into, specified as a two-letter ISO 639-1 code (e.g., 'en', 'fr', 'ja')",
            "enum": [
                "en",
                "fr",
                "es",
                "de",
                "it",
                "pt",
                "nl",
                "ru",
                "ar",
                "zh",
                "ja",
                "ko",
                "th",
                "hi",
                "tr"
            ]
        },
        "expression": {
            "type": "string",
            "description": "The idiomatic expression, proverb, or culturally specific phrase to be translated (e.g., 'break the ice', 'c'est la fin des haricots')"
        },
        "formality_level": {
            "type": "string",
            "description": "Optional: The desired formality level of the translation, affecting the choice of equivalent expression. Options: 'any', 'formal', 'informal', 'neutral'",
            "enum": [
                "any",
                "formal",
                "informal",
                "neutral"
            ]
        }
    },
    "required": [
        "source_language",
        "target_language",
        "expression"
    ]
},
}
