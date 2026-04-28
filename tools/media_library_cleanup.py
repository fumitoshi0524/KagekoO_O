"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import os
    import hashlib
    from collections import defaultdict

    try:
        data = json.loads(payload)
        library_path = data.get('library_path')
        action = data.get('action')
        file_types = data.get('file_types', ['mp3', 'flac', 'mp4', 'mkv', 'jpg', 'png'])
        dry_run = data.get('dry_run', False)

        if not library_path or not os.path.isdir(library_path):
            return json.dumps({'error': 'Library path does not exist or is not accessible'}, ensure_ascii=False)

        result = {'library_path': library_path, 'action': action, 'dry_run': dry_run, 'items_processed': 0, 'issues_found': []}

        if action == 'scan_duplicates':
            size_map = defaultdict(list)
            for root, dirs, files in os.walk(library_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in file_types):
                        fpath = os.path.join(root, file)
                        try:
                            fsize = os.path.getsize(fpath)
                            size_map[fsize].append(fpath)
                        except OSError:
                            result['issues_found'].append({'file': fpath, 'issue': 'unreadable'})

            duplicates = []
            for fsize, paths in size_map.items():
                if len(paths) > 1:
                    hash_map = defaultdict(list)
                    for path in paths:
                        try:
                            with open(path, 'rb') as f:
                                file_hash = hashlib.md5(f.read(8192)).hexdigest()
                            hash_map[file_hash].append(path)
                        except OSError:
                            result['issues_found'].append({'file': path, 'issue': 'unreadable'})
                    for file_hash, file_paths in hash_map.items():
                        if len(file_paths) > 1:
                            duplicates.append({'hash': file_hash, 'files': file_paths[1:]})
                            result['issues_found'].append({'duplicate_of': file_paths[0], 'duplicates': file_paths[1:]})

            result['duplicate_groups'] = len(duplicates)
            result['potential_savings_bytes'] = sum(os.path.getsize(f) for group in duplicates for f in group['files'])
            result['items_processed'] = len(size_map)

        elif action == 'remove_orphans':
            orphan_count = 0
            for root, dirs, files in os.walk(library_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in ['nfo', 'txt', 'srt', 'sub', 'jpg', 'png']):
                        fpath = os.path.join(root, file)
                        base = os.path.splitext(fpath)[0]
                        has_media = any(os.path.exists(base + '.' + ext) for ext in file_types if ext not in ['jpg', 'png'])
                        if not has_media:
                            orphan_count += 1
                            if not dry_run:
                                try:
                                    os.remove(fpath)
                                except OSError as e:
                                    result['issues_found'].append({'file': fpath, 'issue': f'failed_to_remove: {str(e)}'})
                            else:
                                result['issues_found'].append({'orphaned_file': fpath, 'action': 'would_remove'})

            result['orphans_found'] = orphan_count
            result['items_processed'] = orphan_count

        elif action == 'validate_files':
            corrupted = []
            valid_count = 0
            for root, dirs, files in os.walk(library_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in file_types):
                        fpath = os.path.join(root, file)
                        try:
                            with open(fpath, 'rb') as f:
                                header = f.read(32)
                            if len(header) == 0:
                                corrupted.append({'file': fpath, 'issue': 'empty_file'})
                            else:
                                valid_count += 1
                        except OSError:
                            corrupted.append({'file': fpath, 'issue': 'unreadable'})

            result['valid_files'] = valid_count
            result['corrupted_files'] = corrupted
            result['issues_found'] = corrupted
            result['items_processed'] = valid_count + len(corrupted)

        elif action == 'full_cleanup':
            result['sub_actions'] = []
            for sub_action in ['scan_duplicates', 'remove_orphans', 'validate_files']:
                sub_data = {**data, 'action': sub_action}
                sub_result = json.loads(run(json.dumps(sub_data)))
                result['sub_actions'].append(sub_result)
                result['items_processed'] += sub_result.get('items_processed', 0)
                result['issues_found'].extend(sub_result.get('issues_found', []))

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "media_library_cleanup",
    "description": "Analyze and clean up a media library by identifying duplicate files, orphaned metadata, and corrupted media files to free up storage space and maintain library integrity.",
    "category": "system",
    "domain": "entertainment",
    "risk_level": "moderate",
    "schema": {
    "type": "object",
    "properties": {
        "library_path": {
            "type": "string",
            "description": "Absolute path to the media library directory containing music, video, or image files."
        },
        "action": {
            "type": "string",
            "description": "Cleanup operation to perform on the media library.",
            "enum": [
                "scan_duplicates",
                "remove_orphans",
                "validate_files",
                "full_cleanup"
            ]
        },
        "file_types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "mp3",
                    "flac",
                    "mp4",
                    "mkv",
                    "jpg",
                    "png"
                ]
            },
            "description": "Optional: List of file extensions to include in the scan. If omitted, all supported media types are scanned."
        },
        "dry_run": {
            "type": "boolean",
            "description": "Optional: If true, only reports what would be done without making changes. Default is false."
        }
    },
    "required": [
        "library_path",
        "action"
    ]
},
}
