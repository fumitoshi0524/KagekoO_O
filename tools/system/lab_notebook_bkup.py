"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Automatically backup laboratory notebook entries and experiment data files from a designated science project directory to a compressed archive, ensuring data integrity and version tracking for research compliance."""
    import json
    import os
    import shutil
    import datetime

    try:
        data = json.loads(payload)
        required = ['project_id', 'notebook_path', 'archive_format']
        for r in required:
            if r not in data:
                return json.dumps({'error': f'Missing required parameter: {r}'})

        project_id = data['project_id']
        notebook_path = data['notebook_path']
        archive_format = data['archive_format']
        output_dir = data.get('output_dir', '/tmp/backups')
        include_timestamps = data.get('include_timestamps', True)

        # Validate notebook_path exists
        if not os.path.isdir(notebook_path):
            return json.dumps({'error': f'Notebook path does not exist: {notebook_path}'})

        # Create output directory if needed
        os.makedirs(output_dir, exist_ok=True)

        # Build archive filename
        base_name = f'labnotebook_{project_id}'
        if include_timestamps:
            ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name += f'_{ts}'

        # Determine archive extension and format
        ext_map = {
            'zip': 'zip',
            'tar.gz': 'tar.gz',
            '7z': '7z'
        }
        ext = ext_map.get(archive_format, 'zip')
        archive_path = os.path.join(output_dir, f'{base_name}.{ext}')

        # Create archive
        if archive_format == 'zip':
            shutil.make_archive(base_name, 'zip', notebook_path)
            # shutil.make_archive adds .zip automatically, rename to target
            temp_zip = f'{base_name}.zip'
            os.rename(temp_zip, archive_path)
        elif archive_format == 'tar.gz':
            shutil.make_archive(base_name, 'gztar', notebook_path)
            temp_tar = f'{base_name}.tar.gz'
            os.rename(temp_tar, archive_path)
        else:
            # For 7z we use a simple fallback: copy folder then compress via external tool or just copy as zip
            return json.dumps({'error': '7z format not supported in this implementation; use zip or tar.gz.'})

        # Verify archive exists
        if not os.path.isfile(archive_path):
            return json.dumps({'error': 'Archive creation failed - file not found.'})

        # Get file size
        file_size_bytes = os.path.getsize(archive_path)
        file_size_mb = round(file_size_bytes / (1024 * 1024), 2)

        result = {
            'status': 'success',
            'project_id': project_id,
            'archive_path': archive_path,
            'archive_format': archive_format,
            'size_mb': file_size_mb,
            'backup_timestamp': datetime.datetime.now().isoformat()
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': f'Backup failed: {str(e)}'})


TOOL_SPEC = {
    "name": "lab_notebook_bkup",
    "description": "Automatically backup laboratory notebook entries and experiment data files from a designated science project directory to a compressed archive, ensuring data integrity and version tracking for research compliance.",
    "category": "system",
    "domain": "science",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "project_id": {
            "type": "string",
            "description": "Unique identifier for the science project whose notebook data will be backed up."
        },
        "notebook_path": {
            "type": "string",
            "description": "Absolute file path to the directory containing lab notebook entries (e.g., markdown, CSV, images) for the project."
        },
        "archive_format": {
            "type": "string",
            "description": "Compression format for the backup archive.",
            "enum": [
                "zip",
                "tar.gz",
                "7z"
            ]
        },
        "output_dir": {
            "type": "string",
            "description": "Optional: Target directory where the backup archive will be saved. Defaults to a system-defined backup location."
        },
        "include_timestamps": {
            "type": "boolean",
            "description": "Optional: If True, appends a timestamp to the archive filename for versioning.",
            "default": True
        }
    },
    "required": [
        "project_id",
        "notebook_path",
        "archive_format"
    ]
},
}
