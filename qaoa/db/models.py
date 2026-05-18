"""Database models for Kageko (compatibility stubs for history tracking)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FileChange:
    """Record of a file modification within a session."""

    id: str = ""
    session_id: str = ""
    path: str = ""
    hash: str = ""
    created_at: datetime = field(default_factory=datetime.now)
