from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Instinct:
    """An Instinct learned from observations including QAOAObservation records."""
    id: str
    trigger: str
    confidence: float
    domain: str
    source: str
    content: str
    source_repo: str = ""
    source_file: str = ""
    source_type: str = ""
    imported_at: str = ""
    original_source: str = ""
    merged_from: str = ""
    conflict_reason: str = ""
    updated_at: str = ""
    observations: int = 0
    deprecated: bool = False


EvolveType = Literal["command", "skill", "agent"]


@dataclass
class ClusterCandidate:
    key: str
    instincts: list[Instinct] = field(default_factory=list)
    avg_confidence: float = 0.0
    domains: list[str] = field(default_factory=list)
    evolve_type: EvolveType = "skill"
    cluster_score: float = 0.0
    experience_score: float = 0.0
