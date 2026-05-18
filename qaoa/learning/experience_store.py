from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ..config.settings import Settings
from .ecap_migration import upgrade_ecap_v1_to_v2
from .ecap_privacy import sanitize_ecap
from .ecap_serializer import to_ecap_json, to_ecap_markdown
from .experience_models import ExperienceCapsule
from .paths import ensure_learning_dirs
from .store import write_snapshot


def _experience_dirs(settings: Settings) -> tuple[Path, Path]:
    p = ensure_learning_dirs(settings)
    root = p.root / "experience"
    caps = root / "capsules"
    exports = root / "exports"
    caps.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)
    return caps, exports


def save_capsule(settings: Settings, capsule: ExperienceCapsule) -> Path:
    caps_dir, _ = _experience_dirs(settings)
    if not capsule.ecap_id:
        capsule.ecap_id = datetime.now().strftime("ecap-%Y%m%d-%H%M%S")
    now = datetime.now(timezone.utc).isoformat()
    if not capsule.governance.created_at:
        capsule.governance.created_at = now
    capsule.governance.updated_at = now
    out = caps_dir / f"{capsule.ecap_id}.json"
    out.write_text(to_ecap_json(capsule), encoding="utf-8")
    snapshot_capsule_change(settings, "save", capsule)
    return out


def load_capsule(settings: Settings, ecap_id: str) -> ExperienceCapsule | None:
    caps_dir, _ = _experience_dirs(settings)
    path = caps_dir / f"{ecap_id}.json"
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return _capsule_from_dict(obj)
    except Exception:
        return None


def list_capsules(settings: Settings) -> list[ExperienceCapsule]:
    caps_dir, _ = _experience_dirs(settings)
    out: list[ExperienceCapsule] = []
    for f in sorted(caps_dir.glob("*.json")):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
            out.append(_capsule_from_dict(obj))
        except Exception:
            continue
    return out


def export_capsule(
    settings: Settings,
    capsule: ExperienceCapsule,
    *,
    fmt: str,
    output_path: str = "",
    privacy_level: str = "balanced",
) -> Path:
    _, exports = _experience_dirs(settings)
    fmt = fmt.lower().strip()
    if fmt not in {"json", "md"}:
        raise ValueError("fmt must be json or md")
    ext = "json" if fmt == "json" else "md"
    out = Path(output_path).expanduser() if output_path else exports / f"{capsule.ecap_id}.{ext}"
    safe = sanitize_ecap(_capsule_from_dict(asdict(capsule)), level=privacy_level)  # clone + sanitize
    text = to_ecap_json(safe) if fmt == "json" else to_ecap_markdown(safe)
    out.write_text(text, encoding="utf-8")
    snapshot_capsule_change(settings, f"export-{fmt}", capsule)
    return out


def import_capsule_from_text(settings: Settings, text: str, *, force: bool = False) -> tuple[bool, str]:
    try:
        obj = json.loads(text)
    except Exception as e:
        return False, f"Invalid ECAP JSON: {e}"
    cap = _capsule_from_dict(obj)
    if not cap.ecap_id:
        return False, "Missing ecap_id in capsule"
    if (not force) and load_capsule(settings, cap.ecap_id) is not None:
        return False, f"Capsule `{cap.ecap_id}` already exists. Use --force to overwrite."
    save_capsule(settings, cap)
    return True, f"Imported `{cap.ecap_id}`."


def snapshot_capsule_change(settings: Settings, action: str, capsule: ExperienceCapsule) -> Path:
    return write_snapshot(
        settings,
        reason=f"experience-{action}",
        payload={
            "schema_version": capsule.schema_version,
            "ecap_id": capsule.ecap_id,
            "action": action,
            "privacy_level": capsule.governance.privacy_level,
            "payload": asdict(capsule),
        },
    )


def _capsule_from_dict(obj: dict) -> ExperienceCapsule:
    schema = str(obj.get("schema_version", "ecap-v1"))
    if schema in {"ecap-v1", "ecap-v2", "ecap-v3"}:
        return upgrade_ecap_v1_to_v2(obj)
    return upgrade_ecap_v1_to_v2(obj)
