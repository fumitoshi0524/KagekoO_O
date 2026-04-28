"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate original poetry based on topic and style."""
    import json
    import random
    import re

    try:
        data = json.loads(payload)
        
        # Extract and validate inputs
        topic = data.get('topic')
        style = data.get('style')
        if not topic or not style:
            return json.dumps({'error': 'Missing required parameters: topic, style'}, ensure_ascii=False)
        
        mood = data.get('mood', None)
        rhyme_scheme = data.get('rhyme_scheme', 'free')
        lines = data.get('lines', None)
        
        valid_styles = ['haiku', 'sonnet', 'free_verse', 'limerick', 'acrostic']
        if style not in valid_styles:
            return json.dumps({'error': f'Invalid style. Must be one of: {valid_styles}'}, ensure_ascii=False)
        
        # Build poem based on style
        poem_data = {
            'topic': topic,
            'style': style,
            'mood': mood if mood else 'serene',
            'rhyme_scheme': rhyme_scheme,
            'text': '',
            'lines_count': 0,
            'meter': 'variable'
        }
        
        # Simple template-based generation for each style
        word_pools = {
            'nature': ['moon', 'breeze', 'river', 'tree', 'star', 'cloud', 'leaf', 'stream', 'petal', 'rain'],
            'emotions': ['whisper', 'longing', 'joy', 'tears', 'hope', 'dream', 'silence', 'wonder', 'peace'],
            'actions': ['dances', 'flows', 'drifts', 'burns', 'sings', 'grows', 'falls', 'shines']
        }
        
        if style == 'haiku':
            # 3 lines: 5-7-5 syllables
            line1 = f'{random.choice(word_pools["nature"])} {random.choice(word_pools["actions"])}'
            line2 = f'{random.choice(word_pools["emotions"])} {random.choice(word_pools["actions"])} {random.choice(word_pools["nature"])}'
            line3 = f'{random.choice(word_pools["nature"])} {random.choice(word_pools["actions"])}'
            poem_data['text'] = f'{line1}\n{line2}\n{line3}'
            poem_data['lines_count'] = 3
            poem_data['meter'] = '5-7-5 syllables'
            poem_data['rhyme_scheme'] = 'none'
            
        elif style == 'sonnet':
            # 14 lines, iambic pentameter approximation
            lines_list = []
            for i in range(14):
                line = f'The {random.choice(word_pools["nature"])} of {topic} {random.choice(["beckons", "calls", "dances", "flows"])}'
                if i % 2 == 0:
                    line += f' with {random.choice(word_pools["emotions"])}'
                lines_list.append(line)
            poem_data['text'] = '\n'.join(lines_list)
            poem_data['lines_count'] = 14
            poem_data['meter'] = 'iambic pentameter'
            poem_data['rhyme_scheme'] = 'ABAB CDCD EFEF GG' if rhyme_scheme == 'free' else rhyme_scheme
            
        elif style == 'limerick':
            # 5 lines AABBA
            lines_list = [
                f'There once was a {topic} so grand,',
                f'That danced on the {random.choice(word_pools["nature"])}land,',
                f'With a {random.choice(word_pools["emotions"])} sigh,',
                f'It said goodbye,',
                f'And vanished like {random.choice(word_pools["nature"])} in the sand.'
            ]
            poem_data['text'] = '\n'.join(lines_list)
            poem_data['lines_count'] = 5
            poem_data['meter'] = 'anapestic'
            poem_data['rhyme_scheme'] = 'AABBA'
            
        elif style == 'acrostic':
            # First letter of each line spells the topic
            topic_clean = re.sub(r'[^a-zA-Z ]', '', topic).upper().replace(' ', '')
            if not topic_clean:
                topic_clean = 'POEM'
            lines_list = []
            for letter in topic_clean[:12]:  # max 12 lines
                words = random.sample(word_pools['nature'] + word_pools['emotions'], 4)
                line = f'{letter} - {" ".join(words)}'
                lines_list.append(line)
            poem_data['text'] = '\n'.join(lines_list)
            poem_data['lines_count'] = len(lines_list)
            poem_data['meter'] = 'variable'
            poem_data['rhyme_scheme'] = 'none'
            
        else:  # free_verse
            line_count = lines if lines and 1 <= lines <= 24 else 10
            lines_list = []
            for _ in range(line_count):
                line = f'The {random.choice(word_pools["nature"])} of {topic} {random.choice(word_pools["actions"])}'
                if random.random() > 0.5:
                    line += f' with {random.choice(word_pools["emotions"])}'
                lines_list.append(line)
            poem_data['text'] = '\n'.join(lines_list)
            poem_data['lines_count'] = line_count
            poem_data['meter'] = 'free verse'
            poem_data['rhyme_scheme'] = 'none' if rhyme_scheme == 'free' else rhyme_scheme
        
        return json.dumps(poem_data, ensure_ascii=False)
        
    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "poetry_generator",
    "description": "Generate original poetry in various styles (haiku, sonnet, free verse) on a given theme or topic. Returns a poem object with the generated text, style, meter, and rhyme scheme.",
    "category": "generate",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "The theme or subject matter for the poem (e.g., 'autumn leaves', 'ocean waves', 'lost love').",
            "examples": [
                "spring morning",
                "winter solitude",
                "a warrior's farewell"
            ]
        },
        "style": {
            "type": "string",
            "enum": [
                "haiku",
                "sonnet",
                "free_verse",
                "limerick",
                "acrostic"
            ],
            "description": "The poetic form to use. Haiku: 5-7-5 syllables. Sonnet: 14 lines, iambic pentameter. Free verse: no strict meter or rhyme. Limerick: AABBA rhyme. Acrostic: first letters spell the topic.",
            "examples": [
                "haiku",
                "sonnet",
                "free_verse"
            ]
        },
        "mood": {
            "type": "string",
            "enum": [
                "happy",
                "sad",
                "romantic",
                "dark",
                "playful",
                "serene"
            ],
            "description": "Optional: The emotional tone or mood of the poem. If not provided, a mood will be inferred from the topic.",
            "examples": [
                "serene",
                "romantic"
            ]
        },
        "rhyme_scheme": {
            "type": "string",
            "enum": [
                "none",
                "ABAB",
                "AABB",
                "ABBA",
                "ABCB",
                "free"
            ],
            "description": "Optional: Specific end-rhyme pattern. 'none' for no rhyme (free verse), 'free' to let the generator choose. Default: depends on style.",
            "examples": [
                "ABAB",
                "AABB"
            ]
        },
        "lines": {
            "type": "integer",
            "minimum": 1,
            "maximum": 24,
            "description": "Optional: Number of lines for free verse or custom styles. Ignored for fixed forms like haiku (3 lines) or sonnet (14 lines). Default: style-appropriate value.",
            "examples": [
                8,
                12
            ]
        }
    },
    "required": [
        "topic",
        "style"
    ]
},
}
