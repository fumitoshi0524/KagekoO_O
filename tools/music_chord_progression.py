"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random
    
    try:
        data = json.loads(payload)
        
        key = data.get('key')
        genre = data.get('genre')
        length = data.get('length', 4)
        mood = data.get('mood', 'neutral')
        include_seventh = data.get('include_seventh', None)
        
        if not key or not genre:
            return json.dumps({'error': 'key and genre are required'}, ensure_ascii=False)
        
        if length < 2 or length > 8:
            return json.dumps({'error': 'length must be between 2 and 8'}, ensure_ascii=False)
        
        if key not in ['C','Cm','C#','C#m','Db','Dbm','D','Dm','Eb','Ebm','E','Em','F','Fm','F#','F#m','Gb','Gbm','G','Gm','Ab','Abm','A','Am','Bb','Bbm','B','Bm']:
            return json.dumps({'error': f'invalid key: {key}'}, ensure_ascii=False)
        
        if genre not in ['pop','rock','jazz','blues','classical','electronic','folk','r&b','hip-hop','ambient']:
            return json.dumps({'error': f'invalid genre: {genre}'}, ensure_ascii=False)
        
        if include_seventh is None:
            include_seventh = (genre == 'jazz')
        
        is_minor = key.endswith('m')
        root = key.replace('m', '')
        
        # Define chord scale degrees based on major/minor
        if is_minor:
            # Natural minor scale chords
            scale_degrees = ['i', 'ii°', 'III', 'iv', 'v', 'VI', 'VII']
            chord_templates = {
                'i': ['m'],
                'ii°': ['dim'],
                'III': ['M'],
                'iv': ['m'],
                'v': ['m'],
                'VI': ['M'],
                'VII': ['M']
            }
        else:
            scale_degrees = ['I', 'ii', 'iii', 'IV', 'V', 'vi', 'vii°']
            chord_templates = {
                'I': ['M'],
                'ii': ['m'],
                'iii': ['m'],
                'IV': ['M'],
                'V': ['M'],
                'vi': ['m'],
                'vii°': ['dim']
            }
        
        # Genre-specific progression patterns
        genre_patterns = {
            'pop': [['I','V','vi','IV'], ['I','vi','IV','V'], ['ii','V','I','IV']],
            'rock': [['I','IV','V','IV'], ['I','V','vi','IV'], ['I','IV','I','V']],
            'jazz': [['ii','V','I','vi'], ['I','vi','ii','V'], ['III','VI','ii','V']],
            'blues': [['I','IV','I','V'], ['I','IV','V','IV'], ['I','I','IV','I']],
            'classical': [['I','IV','V','I'], ['I','vi','ii','V'], ['I','V','vi','iii']],
            'electronic': [['i','VI','III','VII'], ['I','IV','vi','IV'], ['Am','F','C','G']],
            'folk': [['I','IV','I','V'], ['I','V','vi','IV'], ['I','IV','V','I']],
            'r&b': [['ii','V','I','vi'], ['I','iii','IV','V'], ['vi','IV','I','V']],
            'hip-hop': [['I','IV','vi','V'], ['vi','IV','V','I'], ['i','VII','VI','v']],
            'ambient': [['I','III','IV','VI'], ['i','III','VII','VI'], ['I','IV','I','IV']]
        }
        
        # Get pattern for genre, fallback to pop
        patterns = genre_patterns.get(genre, genre_patterns['pop'])
        
        # Adjust for mood
        if mood == 'sad':
            if is_minor:
                patterns = [p for p in patterns if 'i' in p.lower() or 'v' in p.lower()]
            else:
                patterns = [['vi','IV','I','V'], ['ii','v','i','VII'], ['vi','iii','ii','I']]
        elif mood == 'happy':
            patterns = [p for p in patterns if 'I' in p or 'IV' in p or 'V' in p]
            if not patterns:
                patterns = [['I','IV','V','I'], ['I','V','vi','IV']]
        elif mood == 'tense' or mood == 'dark':
            patterns = [['vii°','III','vi','ii'], ['i','VII','VI','v'], ['ii°','V','i','VII']]
        elif mood == 'uplifting':
            patterns = [['I','IV','V','I'], ['I','V','vi','IV'], ['I','III','IV','V']]
        elif mood == 'nostalgic':
            patterns = [['I','iii','IV','V'], ['vi','V','IV','I'], ['I','vi','IV','V']]
        elif mood == 'mysterious':
            patterns = [['i','VII','VI','v'], ['iv','i','VII','VI'], ['I','vii°','III','vi']]
        
        if not patterns:
            patterns = genre_patterns['pop']
        
        # Pick random pattern
        pattern = random.choice(patterns)
        
        # Build chord names from pattern
        roman_analysis = pattern[:length]
        
        # Map roman numerals to actual chord names
        # This is simplified - in real implementation would use proper music theory
        root_notes = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
        root_index = root_notes.index(root) if root in root_notes else 0
        
        chord_names = []
        for degree in roman_analysis:
            degree_upper = degree.upper()
            degree_num = ['I','II','III','IV','V','VI','VII'].index(degree_upper) if degree_upper in ['I','II','III','IV','V','VI','VII'] else 0
            
            # Calculate note offset (simplified - assumes major scale)
            offsets = [0, 2, 4, 5, 7, 9, 11]
            note_index = (root_index + offsets[degree_num]) % 12
            note = root_notes[note_index]
            
            if is_minor and degree == degree.lower():
                # Minor chords on certain degrees
                if degree_num == 0:
                    chord = note + 'm'
                elif degree_num == 3:
                    chord = note + 'M'
                elif degree_num == 4:
                    chord = note + 'm'
                elif degree_num == 5:
                    chord = note + 'm'
                else:
                    chord = note + 'M'
            else:
                if degree == degree.upper():
                    if degree_num == 1 or degree_num == 2 or degree_num == 5:
                        chord = note + 'm'
                    else:
                        chord = note + 'M'
                else:
                    chord = note + 'm'
            
            # Add seventh if requested
            if include_seventh:
                if 'm' in chord:
                    chord += '7'
                else:
                    chord += 'Maj7'
            
            chord_names.append(chord)
        
        # Determine emotional character
        emotional_characters = {
            'happy': 'Bright and uplifting, major chords dominate',
            'sad': 'Melancholic and introspective, minor chords create depth',
            'tense': 'Unresolved and suspenseful, diminished chords add tension',
            'dark': 'Heavy and brooding, minor and diminished chords create darkness',
            'uplifting': 'Energizing and positive, major chords with strong resolution',
            'nostalgic': 'Warm and reflective, mix of major and minor creates bittersweet feel',
            'peaceful': 'Calm and serene, open harmonies with gentle resolution',
            'dramatic': 'Bold and expressive, unexpected chord changes create impact',
            'mysterious': 'Enigmatic and atmospheric, ambiguous harmonies',
            'neutral': 'Balanced and versatile, suitable for various contexts'
        }
        
        emotional_char = emotional_characters.get(mood, emotional_characters['neutral'])
        
        result = {
            'key': key,
            'genre': genre,
            'mood': mood,
            'length': len(roman_analysis),
            'roman_analysis': roman_analysis,
            'chord_names': chord_names,
            'emotional_character': emotional_char,
            'suggested_use': f'Suitable for {genre} songwriting in {key}. {'Incorporate seventh chords for richer harmony.' if include_seventh else 'Use basic triads for a cleaner sound.'}'
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "music_chord_progression",
    "description": "Generate a musically valid chord progression in a specified key and genre, returning a Roman numeral analysis, chord names, and suggested emotional character for use in songwriting and music production.",
    "category": "generate",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "key": {
            "type": "string",
            "description": "Musical key for the progression (e.g., C, G, Dm, F#m). Must be a standard note name optionally with m for minor.",
            "enum": [
                "C",
                "Cm",
                "C#",
                "C#m",
                "Db",
                "Dbm",
                "D",
                "Dm",
                "Eb",
                "Ebm",
                "E",
                "Em",
                "F",
                "Fm",
                "F#",
                "F#m",
                "Gb",
                "Gbm",
                "G",
                "Gm",
                "Ab",
                "Abm",
                "A",
                "Am",
                "Bb",
                "Bbm",
                "B",
                "Bm"
            ]
        },
        "genre": {
            "type": "string",
            "description": "Musical genre to influence the chord choices and progression style.",
            "enum": [
                "pop",
                "rock",
                "jazz",
                "blues",
                "classical",
                "electronic",
                "folk",
                "r&b",
                "hip-hop",
                "ambient"
            ]
        },
        "length": {
            "type": "integer",
            "description": "Number of chords in the progression (between 2 and 8).",
            "minimum": 2,
            "maximum": 8,
            "default": 4
        },
        "mood": {
            "type": "string",
            "description": "Optional: Desired emotional mood for the progression. Influences chord selection (e.g., happy, sad, tense, dark, uplifting, nostalgic).",
            "enum": [
                "happy",
                "sad",
                "tense",
                "dark",
                "uplifting",
                "nostalgic",
                "peaceful",
                "dramatic",
                "mysterious",
                "neutral"
            ]
        },
        "include_seventh": {
            "type": "boolean",
            "description": "Optional: Whether to include seventh chords in the progression for richer harmony (default true for jazz, false otherwise)."
        }
    },
    "required": [
        "key",
        "genre"
    ]
},
}
