"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json, os, hashlib
    try:
        data = json.loads(payload)
        media_dir = data.get("media_directory")
        scan_type = data.get("scan_type")
        if not media_dir or not scan_type:
            return json.dumps({"error": "Missing required parameters: media_directory and scan_type"})
        if not os.path.isdir(media_dir):
            return json.dumps({"error": f"Directory not found: {media_dir}"})
        
        quality_threshold = data.get("quality_threshold_kbps", 2000)
        
        results = {
            "duplicates": [],
            "orphans": [],
            "low_quality": [],
            "total_reclaimable_mb": 0
        }
        
        # Simulate scanning for files (in real impl would walk directory)
        file_hashes = {}
        for root, dirs, files in os.walk(media_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                if not os.path.isfile(fpath):
                    continue
                ext = os.path.splitext(fname)[1].lower()
                if ext not in ('.mp4', '.mkv', '.avi', '.mov', '.flac', '.mp3', '.srt', '.vtt'):
                    continue
                
                # Simulate file size info
                size_mb = os.path.getsize(fpath) / (1024 * 1024)
                
                if scan_type in ("duplicates", "all"):
                    hasher = hashlib.md5()
                    with open(fpath, "rb") as f:
                        buf = f.read(8192)
                        hasher.update(buf)
                    fhash = hasher.hexdigest()
                    if fhash in file_hashes:
                        results["duplicates"].append({
                            "file": fpath,
                            "duplicate_of": file_hashes[fhash],
                            "size_mb": round(size_mb, 2)
                        })
                        results["total_reclaimable_mb"] += size_mb
                    else:
                        file_hashes[fhash] = fpath
                
                if scan_type in ("orphans", "all"):
                    # Common orphan check: subtitle without media, or thumbnail without video
                    if ext in ('.srt', '.vtt'):
                        base = os.path.splitext(fpath)[0]
                        possible_media = [base + ext for ext in ('.mp4', '.mkv', '.avi', '.mov')]
                        if not any(os.path.exists(pm) for pm in possible_media):
                            results["orphans"].append({
                                "file": fpath,
                                "type": "subtitle_without_media",
                                "size_mb": round(size_mb, 2)
                            })
                            results["total_reclaimable_mb"] += size_mb
                
                if scan_type in ("low_quality", "all"):
                    # Simulated bitrate calculation from file size and assumed duration
                    if ext in ('.mp4', '.mkv', '.avi'):
                        assumed_duration_min = 120  # assumption for movies
                        size_kb = os.path.getsize(fpath) / 1024
                        estimated_bitrate = size_kb / (assumed_duration_min * 60)
                        if estimated_bitrate < quality_threshold:
                            results["low_quality"].append({
                                "file": fpath,
                                "estimated_bitrate_kbps": round(estimated_bitrate, 0),
                                "size_mb": round(size_mb, 2)
                            })
                            results["total_reclaimable_mb"] += size_mb
        
        # Summary
        results["summary"] = {
            "duplicates_found": len(results["duplicates"]),
            "orphans_found": len(results["orphans"]),
            "low_quality_found": len(results["low_quality"]),
            "total_reclaimable_gb": round(results["total_reclaimable_mb"] / 1024, 2)
        }
        
        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


TOOL_SPEC = {
    "name": "media_server_cleanup",
    "description": "Manage and clean media server storage by scanning for duplicate, orphaned, or low-quality media files (movies, episodes, audio tracks, subtitles). Returns a summary of removable items and total estimated space reclaimable, used for routine storage maintenance on entertainment servers.",
    "category": "system",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "media_directory": {
            "type": "string",
            "description": "Filesystem path to the root media directory (e.g., /mnt/media/movies)"
        },
        "scan_type": {
            "type": "string",
            "description": "Type of media cleanup to perform",
            "enum": [
                "duplicates",
                "orphans",
                "low_quality",
                "all"
            ]
        },
        "quality_threshold_kbps": {
            "type": "integer",
            "description": "Optional: Bitrate threshold in kbps; files below this are flagged as low quality when scan_type is low_quality or all"
        }
    },
    "required": [
        "media_directory",
        "scan_type"
    ]
},
}
