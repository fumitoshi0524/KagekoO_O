"""Kageko Learning System — Hermes-aligned.

┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐
│ MemoryStore │  │ NudgeEngine  │  │ SkillStore │  │ Curator  │
│  facts +    │  │  counter-    │  │  workflow  │  │  7-day   │
│  snapshot   │  │  based review│  │  store     │  │  cycle   │
└─────────────┘  └──────────────┘  └────────────┘  └──────────┘
"""

from kageko.learning.memory_store import MemoryStore, Fact
from kageko.learning.nudge_engine import NudgeEngine
from kageko.learning.skill_store import SkillStore, SkillRecord
from kageko.learning.memory import MemoryManager  # backward-compat facade
from kageko.learning.curator import Curator, CuratorConfig, SkillState
from kageko.learning.skills import SkillEngine  # legacy, kept for /skill-extract

__all__ = [
    "MemoryStore", "Fact",
    "NudgeEngine",
    "SkillStore", "SkillRecord",
    "MemoryManager",
    "Curator", "CuratorConfig", "SkillState",
    "SkillEngine",
]
