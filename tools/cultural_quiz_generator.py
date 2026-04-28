"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a multiple-choice quiz question about world cultures."""
    import json
    import random
    try:
        data = json.loads(payload)
        topic = data.get('topic')
        region = data.get('region', 'random')
        difficulty = data.get('difficulty', 'medium')
        exclude_topics = data.get('exclude_topics', [])
        
        if not topic:
            return json.dumps({'error': 'Missing required parameter: topic'}, ensure_ascii=False)
        
        # Comprehensive cultural question database
        # Each entry: (question, options, correct_index, cultural_fact, topic, region, difficulty)
        culture_db = [
            # Festivals
            ('Which festival is known as the "Festival of Colors" and is celebrated by Hindus worldwide?', ['Diwali', 'Holi', 'Eid al-Fitr', 'Day of the Dead'], 1, 'Holi celebrates the victory of good over evil and the arrival of spring, with participants throwing colored powder and water.', 'festivals', 'India', 'easy'),
            ('During which festival do Japanese people visit family graves and honor their ancestors?', ['Hanami', 'Obon', 'Shogatsu', 'Tanabata'], 1, 'Obon is a Buddhist custom that has been observed in Japan for over 500 years, featuring Bon Odori dances.', 'festivals', 'Japan', 'medium'),
            ('The Inti Raymi festival, celebrating the sun god, is an ancient tradition of which indigenous culture?', ['Aztec', 'Maya', 'Inca', 'Mapuche'], 2, 'Inti Raymi was banned by Spanish colonizers in 1535 but was reconstructed in 1944 and is now held annually in Cusco, Peru.', 'festivals', 'Peru', 'hard'),
            # Traditions
            ('In many East Asian cultures, what color is traditionally associated with weddings and symbolizes luck and joy?', ['White', 'Gold', 'Red', 'Blue'], 2, 'Red is considered auspicious in Chinese culture, appearing in weddings, New Year celebrations, and other joyful occasions.', 'traditions', 'East Asia', 'easy'),
            ('Which traditional Hawaiian practice involves garlands made of flowers, leaves, or shells given as gifts?', ['Hula', 'Lei making', 'Luau', 'Tattooing'], 1, 'The lei is a symbol of aloha, given to welcome visitors, celebrate achievements, or express affection in Hawaiian culture.', 'traditions', 'Hawaii', 'medium'),
            ('The tradition of "Hyecho" or traveling on foot to holy sites is particularly important in which religion?', ['Islam', 'Hinduism', 'Buddhism', 'Shinto'], 2, 'Buddhist pilgrimage traditions date back to the time of the Buddha himself, with sites like Bodh Gaya and Sarnath being major destinations.', 'traditions', 'Asia', 'hard'),
            # Cuisine
            ('Which fermented tea is a traditional staple in Mongolia, often mixed with milk, butter, and salt?', ['Matcha', 'Suutei tsai', 'Chai', 'Pu-erh'], 1, 'Suutei tsai (salty milk tea) is a central part of Mongolian hospitality and is often served with buuz (dumplings).', 'cuisine', 'Mongolia', 'medium'),
            ('Fufu, a starchy dough-like food made from cassava or yams, is a staple in which region?', ['Southeast Asia', 'West Africa', 'South America', 'Caribbean'], 1, 'Fufu is typically eaten with soups or stews and is a unifying food across many West African countries like Ghana, Nigeria, and Ivory Coast.', 'cuisine', 'West Africa', 'easy'),
            # Art
            ('The intricate art of paper folding that originated in Japan is called what?', ['Origami', 'Kirigami', 'Sumi-e', 'Ukiyo-e'], 0, 'Origami comes from the Japanese words "oru" (to fold) and "kami" (paper), with traditions dating back to the 17th century.', 'art', 'Japan', 'easy'),
            ('Which indigenous Australian art form uses dots to depict stories and Dreamtime legends?', ['Bark painting', 'Dot painting', 'Rock art', 'Weaving'], 1, 'Dot painting originated with the Papunya Tula artists in the 1970s and uses intricate dot patterns to represent sacred symbols and stories.', 'art', 'Australia', 'medium'),
            # Music
            ('The sitar, a plucked string instrument, is most associated with the classical music of which country?', ['Iran', 'India', 'Turkey', 'Egypt'], 1, 'The sitar gained worldwide fame through the work of Ravi Shankar and has influenced Western musicians like The Beatles.', 'music', 'India', 'easy'),
            ('Flamenco, combining guitar, song, and dance, originated in which Spanish region?', ['Catalonia', 'Basque Country', 'Andalusia', 'Galicia'], 2, 'Flamenco developed from the fusion of Romani, Moorish, and Andalusian musical traditions and is recognized by UNESCO.', 'music', 'Spain', 'medium'),
            # Dance
            ('The traditional Hawaiian dance that tells stories through movement and chants is called what?', ['Hula', 'Tahitian', 'Siva', 'Haka'], 0, 'Hula is a sacred art form that preserves Hawaiian history and mythology through carefully choreographed movements and oli (chants).', 'dance', 'Hawaii', 'easy'),
            # Literature
            ('The ancient Indian epic "The Mahabharata" is written primarily in which language?', ['Hindi', 'Tamil', 'Sanskrit', 'Pali'], 2, 'The Mahabharata is the longest epic poem ever written, with about 1.8 million words, and dates back to around 400 BCE.', 'literature', 'India', 'medium'),
            # History
            ('The ancient city of Petra, famous for its rock-cut architecture, was the capital of which civilization?', ['Roman', 'Nabataean', 'Egyptian', 'Greek'], 1, 'Petra, located in modern-day Jordan, was a major trading hub from the 4th century BCE and is now a UNESCO World Heritage site.', 'history', 'Jordan', 'hard'),
            # Architecture
            ('The stepwells, known as "baolis", are an architectural feature most commonly found in which country?', ['India', 'Iran', 'Ethiopia', 'Yemen'], 0, 'Stepwells are intricate structures built to access groundwater, with the Rani ki Vav in Gujarat being one of the most famous examples.', 'architecture', 'India', 'medium'),
            # Clothing
            ('The kimono, with its T-shaped silhouette and wide sash called an obi, is the traditional garment of which country?', ['China', 'Korea', 'Japan', 'Vietnam'], 2, 'Kimono means "thing to wear" in Japanese and can be traced back to the Heian period (794-1185 CE).', 'clothing', 'Japan', 'easy'),
            ('The colorful woven textiles made by the Maya people, often featuring intricate geometric patterns, are known as what?', ['Huipil', 'Poncho', 'Serape', 'Ruanas'], 0, 'Huipils are traditional blouses worn by indigenous women in Guatemala and southern Mexico, with each community having distinctive patterns.', 'clothing', 'Central America', 'hard'),
        ]
        
        # Filter by topic
        filtered = [q for q in culture_db if q[4] == topic and topic not in exclude_topics]
        
        if not filtered:
            return json.dumps({'error': f'No quiz questions available for topic: {topic}'}, ensure_ascii=False)
        
        # Further filter by region if specified
        if region != 'random':
            region_filtered = [q for q in filtered if q[5].lower() == region.lower()]
            if region_filtered:
                filtered = region_filtered
        
        # Filter by difficulty if specified
        diff_map = {'easy': 0, 'medium': 1, 'hard': 2}
        diff_filtered = [q for q in filtered if q[6] == difficulty]
        if diff_filtered:
            filtered = diff_filtered
        
        # Pick a random question
        question_data = random.choice(filtered)
        
        result = {
            'question': question_data[0],
            'options': question_data[1],
            'correct_index': question_data[2],
            'cultural_fact': question_data[3],
            'topic': question_data[4],
            'region': question_data[5],
            'difficulty': question_data[6]
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "cultural_quiz_generator",
    "description": "Generate a multiple-choice quiz question about world cultures, covering topics like traditions, festivals, arts, history, or cultural practices. Returns a question, four answer options, the correct answer index, and a brief cultural fact.",
    "category": "generate",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "The cultural topic area for the quiz question. Choose from a predefined list of cultural categories.",
            "enum": [
                "festivals",
                "traditions",
                "cuisine",
                "art",
                "music",
                "dance",
                "literature",
                "history",
                "architecture",
                "clothing"
            ]
        },
        "region": {
            "type": "string",
            "description": "Optional: Target geographic region or culture to focus on (e.g., 'Japan', 'West Africa', 'Latin America', 'Scandinavia'). If not specified, a random world culture is selected.",
            "default": "random"
        },
        "difficulty": {
            "type": "string",
            "description": "Optional: Difficulty level of the quiz question, affecting obscurity of the cultural fact.",
            "enum": [
                "easy",
                "medium",
                "hard"
            ],
            "default": "medium"
        },
        "exclude_topics": {
            "type": "array",
            "description": "Optional: List of topic areas to avoid when generating the question. Useful for preventing repetition.",
            "items": {
                "type": "string",
                "enum": [
                    "festivals",
                    "traditions",
                    "cuisine",
                    "art",
                    "music",
                    "dance",
                    "literature",
                    "history",
                    "architecture",
                    "clothing"
                ]
            },
            "uniqueItems": true
        }
    },
    "required": [
        "topic"
    ]
},
}
