"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for literary works by title, author, genre, period, or national tradition and retrieve structured metadata."""
    import json
    import re
    from datetime import datetime

    try:
        data = json.loads(payload)
        title = data.get("title", "")
        if not title or not isinstance(title, str) or len(title.strip()) == 0:
            return json.dumps({"error": "title is required and must be a non-empty string"}, ensure_ascii=False)

        author = data.get("author", "")
        if author and not isinstance(author, str):
            return json.dumps({"error": "author must be a string"}, ensure_ascii=False)

        genres = data.get("genre", [])
        if not isinstance(genres, list):
            return json.dumps({"error": "genre must be a list of strings"}, ensure_ascii=False)

        period = data.get("period", "")
        if period and not isinstance(period, str):
            return json.dumps({"error": "period must be a string"}, ensure_ascii=False)

        language = data.get("language", "")
        if language and (not isinstance(language, str) or len(language) != 2):
            return json.dumps({"error": "language must be a 2-letter ISO 639-1 code"}, ensure_ascii=False)

        max_results = data.get("max_results", 10)
        if not isinstance(max_results, int) or max_results < 1 or max_results > 50:
            max_results = 10

        # comprehensive literary works database
        literary_works = [
            {"title": "Don Quixote", "author": "Miguel de Cervantes", "genre": ["novel"], "period": "Renaissance", "language": "es", "year": 1605, "themes": ["reality vs illusion", "chivalry", "madness"], "reception": "Considered one of the greatest works of fiction ever published, it has been translated into over 100 languages."},
            {"title": "One Hundred Years of Solitude", "author": "Gabriel García Márquez", "genre": ["novel"], "period": "Magic Realism", "language": "es", "year": 1967, "themes": ["family", "memory", "history"], "reception": "Widely acclaimed as a masterpiece of magical realism and a defining work of Latin American literature."},
            {"title": "Hamlet", "author": "William Shakespeare", "genre": ["drama", "tragedy"], "period": "Renaissance", "language": "en", "year": 1603, "themes": ["revenge", "madness", "death"], "reception": "One of Shakespeare's most performed and studied plays, renowned for its psychological depth."},
            {"title": "The Tale of Genji", "author": "Murasaki Shikibu", "genre": ["novel"], "period": "Heian", "language": "ja", "year": 1008, "themes": ["love", "court life", "impermanence"], "reception": "Often called the world's first novel, it remains a cornerstone of Japanese literature."},
            {"title": "Les Misérables", "author": "Victor Hugo", "genre": ["novel"], "period": "Romanticism", "language": "fr", "year": 1862, "themes": ["justice", "redemption", "social inequality"], "reception": "A monumental work of French literature that has inspired numerous adaptations across media."},
            {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "genre": ["novel"], "period": "Modernism", "language": "en", "year": 1925, "themes": ["the American Dream", "wealth", "love"], "reception": "Regarded as a definitive portrait of the Jazz Age and a critique of the American Dream."},
            {"title": "The Odyssey", "author": "Homer", "genre": ["epic poetry"], "period": "Classical", "language": "grc", "year": -800, "themes": ["journey", "heroism", "homecoming"], "reception": "One of the foundational works of Western literature, studied for its narrative structure and character development."},
            {"title": "War and Peace", "author": "Leo Tolstoy", "genre": ["novel"], "period": "Realism", "language": "ru", "year": 1869, "themes": ["war", "fate", "family"], "reception": "Praised for its sweeping narrative and deep philosophical meditations on history and society."},
            {"title": "The Divine Comedy", "author": "Dante Alighieri", "genre": ["epic poetry"], "period": "Medieval", "language": "it", "year": 1320, "themes": ["afterlife", "sin", "salvation"], "reception": "A cornerstone of Italian literature and one of the greatest poems ever written."},
            {"title": "Pride and Prejudice", "author": "Jane Austen", "genre": ["novel"], "period": "Romanticism", "language": "en", "year": 1813, "themes": ["class", "marriage", "reputation"], "reception": "Beloved for its wit and social commentary, it remains one of the most popular novels in English literature."},
            {"title": "The Brothers Karamazov", "author": "Fyodor Dostoevsky", "genre": ["novel"], "period": "Realism", "language": "ru", "year": 1880, "themes": ["faith", "doubt", "free will"], "reception": "Widely regarded as Dostoevsky's masterpiece and one of the greatest novels of all time."},
            {"title": "Things Fall Apart", "author": "Chinua Achebe", "genre": ["novel"], "period": "Postcolonial", "language": "en", "year": 1958, "themes": ["colonialism", "identity", "tradition vs change"], "reception": "A seminal work of African literature that has sold millions of copies worldwide."},
            {"title": "The Thousand and One Nights", "author": "Anonymous", "genre": ["short story", "folk tale"], "period": "Medieval", "language": "ar", "year": 800, "themes": ["storytelling", "fate", "wisdom"], "reception": "A influential collection of Middle Eastern folk tales that has shaped global storytelling traditions."},
            {"title": "The Metamorphosis", "author": "Franz Kafka", "genre": ["novella", "absurdist"], "period": "Modernism", "language": "de", "year": 1915, "themes": ["alienation", "identity", "family"], "reception": "A landmark work of existential and absurdist literature that continues to provoke interpretation."},
            {"title": "Journey to the West", "author": "Wu Cheng'en", "genre": ["novel"], "period": "Ming Dynasty", "language": "zh", "year": 1592, "themes": ["pilgrimage", "redemption", "buddhism"], "reception": "One of the Four Great Classical Novels of Chinese literature, beloved for its adventure and allegory."},
            {"title": "Ficciones", "author": "Jorge Luis Borges", "genre": ["short story"], "period": "Modernism", "language": "es", "year": 1944, "themes": ["labyrinths", "infinity", "reality"], "reception": "A groundbreaking collection that redefined the possibilities of short fiction and influenced postmodern literature."},
            {"title": "The Little Prince", "author": "Antoine de Saint-Exupéry", "genre": ["novella", "fable"], "period": "Modernism", "language": "fr", "year": 1943, "themes": ["childhood", "imagination", "love"], "reception": "One of the best-selling books in history, translated into over 300 languages."},
            {"title": "Invisible Man", "author": "Ralph Ellison", "genre": ["novel"], "period": "Modernism", "language": "en", "year": 1952, "themes": ["race", "identity", "invisibility"], "reception": "A landmark of American literature that won the National Book Award and remains widely studied."},
            {"title": "The Ramayana", "author": "Valmiki", "genre": ["epic poetry"], "period": "Classical", "language": "sa", "year": -500, "themes": ["duty", "devotion", "good vs evil"], "reception": "A foundational text of Indian culture and literature, with enduring influence across South and Southeast Asia."},
            {"title": "The Lord of the Rings", "author": "J.R.R. Tolkien", "genre": ["novel", "fantasy"], "period": "Modern", "language": "en", "year": 1954, "themes": ["power", "friendship", "sacrifice"], "reception": "One of the most popular and influential fantasy series ever written, creating the modern fantasy genre."}
        ]

        # filter by title (case-insensitive partial match)
        query = title.strip().lower()
        results = [w for w in literary_works if query in w["title"].lower()]

        # filter by author if specified
        if author:
            author_query = author.strip().lower()
            results = [w for w in results if author_query in w["author"].lower()]

        # filter by genres if specified
        if genres:
            genres_lower = [g.lower() for g in genres]
            results = [w for w in results if any(g in [x.lower() for x in w["genre"]] for g in genres_lower)]

        # filter by period if specified
        if period:
            period_query = period.strip().lower()
            results = [w for w in results if period_query in w["period"].lower()]

        # filter by language if specified
        if language:
            lang_code = language.strip().lower()
            results = [w for w in results if w["language"] == lang_code]

        # sort by year (ascending)
        results.sort(key=lambda w: w["year"])

        # limit results
        limited = results[:max_results]

        return json.dumps({
            "results": limited,
            "count": len(limited),
            "total_matches": len(results)
        }, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"An unexpected error occurred: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "literary_work_search",
    "description": "Search for literary works by title, author, genre, period, or national tradition and retrieve structured metadata including publication year, original language, major themes, and critical reception summaries.",
    "category": "search",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Full or partial title of the literary work to search for"
        },
        "author": {
            "type": "string",
            "description": "Optional: name of the author to filter results by"
        },
        "genre": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: list of literary genres to filter by (e.g., novel, poetry, drama, short story, essay)"
        },
        "period": {
            "type": "string",
            "description": "Optional: literary period or movement (e.g., Romanticism, Modernism, Postcolonial, Renaissance)"
        },
        "language": {
            "type": "string",
            "description": "Optional: ISO 639-1 language code of the original work (e.g., en, fr, es, ja, ar)"
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: maximum number of results to return (default 10, max 50)",
            "minimum": 1,
            "maximum": 50
        }
    },
    "required": [
        "title"
    ]
},
}
