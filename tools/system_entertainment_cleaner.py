"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Scans the system for temporary entertainment files and returns a report of deletable items."""
    import json
    import os
    import time
    from pathlib import Path

    try:
        data = json.loads(payload)
        scan_path = data.get('scan_path')
        media_types = data.get('media_types')
        min_age_days = data.get('min_age_days', 7)
        dry_run = data.get('dry_run', True)

        if not scan_path or not os.path.isdir(scan_path):
            return json.dumps({'error': 'Invalid or non-existent scan_path directory'})
        if not media_types or not isinstance(media_types, list):
            return json.dumps({'error': 'media_types must be a non-empty list'})

        # Known entertainment cache directories and extensions (simplified demo)
        known_cache_dirs = {
            'music': ['Music', '.cache/music', 'AppData/Local/Music'],
            'video': ['Videos', '.cache/video', 'AppData/Local/Video'],
            'game': ['.cache/game', 'AppData/Local/Game', 'Games'],
            'streaming': ['.cache/streaming', 'AppData/Local/Streaming'],
        }
        known_extensions = {
            'music': ['.mp3', '.flac', '.wav', '.aac', '.ogg'],
            'video': ['.mp4', '.mkv', '.avi', '.mov', '.wmv'],
            'game': ['.pak', '.cache', '.tmp', '.dat'],
            'streaming': ['.ts', '.m3u8', '.partial', '.tmp'],
        }

        current_time = time.time()
        age_seconds = min_age_days * 86400
        report = []
        total_size = 0

        # Determine which types to scan
        if 'all' in media_types:
            types_to_scan = list(known_cache_dirs.keys())
        else:
            types_to_scan = [t for t in media_types if t in known_cache_dirs]

        for mtype in types_to_scan:
            dirs_to_check = known_cache_dirs.get(mtype, [])
            extensions = known_extensions.get(mtype, [])
            for rel_dir in dirs_to_check:
                full_path = os.path.join(scan_path, rel_dir)
                if not os.path.isdir(full_path):
                    continue
                try:
                    for root, dirs, files in os.walk(full_path):
                        for fname in files:
                            ext = os.path.splitext(fname)[1].lower()
                            if ext in extensions:
                                fpath = os.path.join(root, fname)
                                try:
                                    fstat = os.stat(fpath)
                                    file_age = current_time - fstat.st_mtime
                                    if file_age > age_seconds:
                                        report.append({
                                            'file': fpath,
                                            'size_bytes': fstat.st_size,
                                            'last_modified': time.ctime(fstat.st_mtime),
                                            'media_type': mtype
                                        })
                                        total_size += fstat.st_size
                                except (OSError, PermissionError):
                                    continue
                except (OSError, PermissionError):
                    continue

        # Sort report by size descending
        report.sort(key=lambda x: x['size_bytes'], reverse=True)

        result = {
            'total_files': len(report),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'dry_run': dry_run,
            'files': report[:100]  # Limit report to first 100 files
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {e}'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {e}'})



TOOL_SPEC = {
    "name": "system_entertainment_cleaner",
    "description": "Scans the system for temporary entertainment files (music, video, game caches, streaming buffers) and returns a report of deletable items with size estimates, to free up disk space used by entertainment applications.",
    "category": "system",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "scan_path": {
            "type": "string",
            "description": "Root directory path to scan for entertainment cache files (e.g., user home, temp folders). Must be an absolute path."
        },
        "media_types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "music",
                    "video",
                    "game",
                    "streaming",
                    "all"
                ]
            },
            "description": "List of entertainment media types to target for cleaning. 'all' includes every type.",
            "minItems": 1
        },
        "min_age_days": {
            "type": "integer",
            "description": "Optional: Minimum age of files in days to consider for deletion (files older than this will be included). Defaults to 7.",
            "minimum": 0,
            "default": 7
        },
        "dry_run": {
            "type": "boolean",
            "description": "Optional: If true, only report files without deleting. Default true.",
            "default": true
        }
    },
    "required": [
        "scan_path",
        "media_types"
    ]
},
}
