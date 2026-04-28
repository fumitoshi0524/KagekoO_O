"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        show = data.get('show_title')
        season = data.get('season_number')
        episode = data.get('episode_number')
        status = data.get('status')
        rating = data.get('rating')
        notify = data.get('notify_season_complete', False)

        if not show or not season or not episode or not status:
            return json.dumps({'error': 'Missing required fields: show_title, season_number, episode_number, status'})

        # Simulated database lookup: we'll assume the show exists and has 10 episodes per season for demo
        # In real implementation, query a show database to get total episodes in season
        total_eps_in_season = 10  # placeholder
        season_complete = False

        if status == 'watched':
            if rating is not None and (rating < 1 or rating > 10):
                return json.dumps({'error': 'Rating must be between 1 and 10'})
            # Mark in DB as watched, store rating
            # For demonstration, assume successful update
            # Check if this completes the season
            # Simulate that all previous episodes were already watched (in a real app, query DB)
            # Here we just check if episode is the last one
            if episode == total_eps_in_season:
                season_complete = True
        elif status == 'unwatched':
            # Reset episode status
            pass
        elif status == 'in_progress':
            # Mark as partially watched
            pass
        else:
            return json.dumps({'error': f'Invalid status: {status}'})

        result = {
            'show_title': show,
            'season_number': season,
            'episode_number': episode,
            'status': status,
            'rating': rating if status == 'watched' else None
        }
        if notify and season_complete:
            result['season_complete'] = True
            result['message'] = f'Season {season} of {show} is now fully watched!'
        else:
            result['season_complete'] = False

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "tv_show_episode_tracker",
    "description": "Update the watched status and rating for a specific episode of a TV show, tracking user progress and optionally notifying completion of a season.",
    "category": "operations",
    "domain": "entertainment",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "show_title": {
            "type": "string",
            "description": "Title of the TV show (e.g., 'Breaking Bad'). Must match a known show in the database."
        },
        "season_number": {
            "type": "integer",
            "description": "Season number of the episode (starting from 1)."
        },
        "episode_number": {
            "type": "integer",
            "description": "Episode number within the season (starting from 1)."
        },
        "status": {
            "type": "string",
            "enum": [
                "watched",
                "unwatched",
                "in_progress"
            ],
            "description": "Set the watch status for this episode: 'watched' marks it complete, 'unwatched' resets it, 'in_progress' marks it partially viewed."
        },
        "rating": {
            "type": "integer",
            "description": "Optional: User rating for the episode from 1 to 10 (whole number). Only valid when status is 'watched'.",
            "minimum": 1,
            "maximum": 10
        },
        "notify_season_complete": {
            "type": "boolean",
            "description": "Optional: If true and this episode completes a season (all episodes in the season are now watched), return a special notification flag.",
            "default": false
        }
    },
    "required": [
        "show_title",
        "season_number",
        "episode_number",
        "status"
    ]
},
}
