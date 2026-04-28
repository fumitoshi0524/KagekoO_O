"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import os
    import hashlib
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        folder_path = data.get('folder_path')
        scan_mode = data.get('scan_mode')
        max_age_days = data.get('max_file_age_days', 365)
        min_dup_mb = data.get('min_duplicate_size_mb', 1.0)
        dry_run = data.get('dry_run', True)

        if not folder_path or not os.path.isdir(folder_path):
            return json.dumps({'error': 'Invalid folder path'})

        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        min_bytes = int(min_dup_mb * 1024 * 1024)

        report = {
            'folder': folder_path,
            'total_scanned_files': 0,
            'total_size_bytes': 0,
            'candidates_for_deletion': [],
            'total_savings_bytes': 0
        }

        seen_hashes = {}
        seen_names = {}

        for root, dirs, files in os.walk(folder_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                try:
                    stat = os.stat(file_path)
                    report['total_scanned_files'] += 1
                    report['total_size_bytes'] += stat.st_size
                    mod_time = datetime.fromtimestamp(stat.st_mtime)

                    # Check for old files
                    if mod_time < cutoff_date and stat.st_size > min_bytes:
                        report['candidates_for_deletion'].append({
                            'path': file_path,
                            'reason': 'old_unused',
                            'size_bytes': stat.st_size,
                            'last_modified': mod_time.isoformat()
                        })
                        report['total_savings_bytes'] += stat.st_size

                    # Duplicate detection
                    if scan_mode == 'deep' and stat.st_size > min_bytes:
                        with open(file_path, 'rb') as f:
                            content_hash = hashlib.md5(f.read()).hexdigest()
                        if content_hash in seen_hashes:
                            dup_path = seen_hashes[content_hash]
                            if dup_path != file_path:
                                report['candidates_for_deletion'].append({
                                    'path': file_path,
                                    'reason': 'duplicate_content',
                                    'size_bytes': stat.st_size,
                                    'duplicate_of': dup_path
                                })
                                report['total_savings_bytes'] += stat.st_size
                        else:
                            seen_hashes[content_hash] = file_path

                    elif scan_mode == 'quick':
                        base_name = file_name.lower()
                        if base_name in seen_names:
                            dup_path = seen_names[base_name]
                            if dup_path != file_path:
                                report['candidates_for_deletion'].append({
                                    'path': file_path,
                                    'reason': 'duplicate_name',
                                    'size_bytes': stat.st_size,
                                    'duplicate_of': dup_path
                                })
                                report['total_savings_bytes'] += stat.st_size
                        else:
                            seen_names[base_name] = file_path

                except Exception as e:
                    report['candidates_for_deletion'].append({
                        'path': file_path,
                        'reason': f'error_accessing: {str(e)}',
                        'size_bytes': 0
                    })

        # Perform cleanup if not dry_run
        if not dry_run:
            deleted_count = 0
            for candidate in report['candidates_for_deletion']:
                try:
                    os.remove(candidate['path'])
                    deleted_count += 1
                    candidate['deleted'] = True
                except Exception as e:
                    candidate['deleted'] = False
                    candidate['delete_error'] = str(e)
            report['items_deleted'] = deleted_count
        else:
            report['items_deleted'] = 0

        report['dry_run'] = dry_run
        return json.dumps(report, ensure_ascii=False, default=str)

    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "personal_folder_cleaner",
    "description": "Analyze and clean up personal document folders on the filesystem by identifying duplicate files, large unused files, and outdated temporary items, returning a report of deletable items with size savings and risk assessment before cleanup.",
    "category": "system",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "folder_path": {
            "type": "string",
            "description": "Absolute path to the personal folder to be cleaned (e.g., /home/user/Documents)"
        },
        "scan_mode": {
            "type": "string",
            "enum": [
                "quick",
                "deep"
            ],
            "description": "Scan mode: 'quick' checks common temporary files and duplicate names; 'deep' also checks content hashes for duplicates and age of files"
        },
        "max_file_age_days": {
            "type": "integer",
            "description": "Optional: Maximum age in days for files considered unused (e.g., 365 means files not modified in a year)",
            "minimum": 1,
            "default": 365
        },
        "min_duplicate_size_mb": {
            "type": "number",
            "description": "Optional: Minimum file size in MB for duplicate detection to avoid false positives on small files",
            "minimum": 0.1,
            "default": 1.0
        },
        "dry_run": {
            "type": "boolean",
            "description": "Optional: If true, only report what would be cleaned without actually deleting anything",
            "default": true
        }
    },
    "required": [
        "folder_path",
        "scan_mode"
    ]
},
}
