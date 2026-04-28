"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        topic_type = data.get('topic_type')
        topic_name = data.get('topic_name')
        language = data.get('language', 'English')
        story_length = data.get('story_length', 'medium')
        audience = data.get('audience', 'general')
        
        if not topic_type or not topic_name:
            return json.dumps({'error': 'topic_type and topic_name are required'}, ensure_ascii=False)
        
        # Simulated story generation logic
        length_words = {'short': 175, 'medium': 350, 'long': 550}
        target_words = length_words.get(story_length, 350)
        
        # In a real implementation, would call an LLM or knowledge base
        story_templates = {
            'site': f"In the heart of {topic_name} lies a story of ancient craftsmanship and cultural pride. Built centuries ago by skilled artisans, this site stands as a testament to the ingenuity of its people. Visitors from around the world come to marvel at its architecture and absorb the spiritual energy that still lingers in its walls. The site embodies the soul of a civilization that valued harmony with nature and divine inspiration.",
            'tradition': f"The tradition of {topic_name} has been passed down through generations, connecting families and communities with their roots. Each year, as the season arrives, people gather to participate in rituals that honor their ancestors and celebrate life's cycles. The vibrant colors, sounds, and flavors create an immersive experience that strengthens cultural identity and fosters unity among participants.",
            'figure': f"{topic_name} remains one of the most influential figures in cultural history. Through their work and life, they challenged conventions and inspired countless others to express their own truths. Their legacy is not merely in museums or books, but in the hearts of those who continue to find meaning in their contributions to art, literature, or philosophy.",
            'event': f"The event of {topic_name} marked a profound turning point in cultural development. It was a moment when ideas collided and new possibilities emerged, reshaping how people understood themselves and the world. The ripple effects of this event continue to be felt today in art forms, social structures, and collective memory."
        }
        
        base_story = story_templates.get(topic_type, f"{topic_name} holds a special place in the cultural heritage of its region. Its significance spans centuries and continues to inspire new generations.")
        
        # Adjust for audience
        if audience == 'children':
            base_story = base_story.replace('artisans', 'clever makers').replace('divine inspiration', 'wonderful dreams')
        elif audience == 'scholarly':
            base_story += f"\n\nScholarly analysis indicates that the cultural context of {topic_name} is deeply intertwined with broader historical forces, requiring careful examination of primary sources and archaeological evidence."
        
        # Word count adjustment (simplified)
        words = base_story.split()
        if len(words) < target_words:
            import random
            filler = ["Indeed,", "Furthermore,", "Notably,", "Remarkably,", "Interestingly,"]
            while len(words) < target_words:
                idx = random.randint(0, len(words) - 1)
                words.insert(idx, random.choice(filler))
        elif len(words) > target_words:
            words = words[:target_words]
        
        final_story = ' '.join(words)
        
        result = {
            'story': final_story,
            'metadata': {
                'topic_type': topic_type,
                'topic_name': topic_name,
                'language': language,
                'length': story_length,
                'audience': audience,
                'word_count': len(words)
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "cultural_heritage_story_generator",
    "description": "Generate a short narrative story based on a specific cultural heritage site, tradition, or historical figure, incorporating authentic cultural elements and educational context.",
    "category": "generate",
    "domain": "culture",
    "risk_level": "low",
    "schema": {
    "type": "object",
    "properties": {
        "topic_type": {
            "type": "string",
            "description": "The type of cultural subject: 'site' (monument, building, archaeological site), 'tradition' (festival, ritual, craft), 'figure' (historical person, artist, writer), 'event' (historical event, cultural milestone)",
            "enum": [
                "site",
                "tradition",
                "figure",
                "event"
            ]
        },
        "topic_name": {
            "type": "string",
            "description": "Name of the specific cultural heritage entity (e.g., 'Machu Picchu', 'Chinese New Year', 'Frida Kahlo', 'The Renaissance')"
        },
        "language": {
            "type": "string",
            "description": "Language for the generated story content (e.g., 'English', 'Spanish', 'French', 'Chinese', 'Arabic'). Default is 'English'.",
            "default": "English"
        },
        "story_length": {
            "type": "string",
            "description": "Approximate length of the generated story: 'short' (150-200 words), 'medium' (300-400 words), 'long' (500-600 words)",
            "enum": [
                "short",
                "medium",
                "long"
            ],
            "default": "medium"
        },
        "audience": {
            "type": "string",
            "description": "Target audience for the story: 'general' (broad public), 'children' (simplified, engaging), 'scholarly' (academic, detailed). Default is 'general'.",
            "default": "general"
        }
    },
    "required": [
        "topic_type",
        "topic_name"
    ]
},
}
