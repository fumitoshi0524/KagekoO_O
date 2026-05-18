from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config.settings import Settings


@dataclass(frozen=True)
class LearningPaths:
    root: Path
    observations_file: Path
    instincts_personal_dir: Path
    instincts_inherited_dir: Path
    evolved_skills_dir: Path
    evolved_commands_dir: Path
    evolved_agents_dir: Path
    team_experience_capsules_dir: Path
    team_experience_exports_dir: Path
    team_experience_feedback_file: Path


def get_learning_paths(settings: Settings) -> LearningPaths:
    data_dir = settings.ensure_data_directory()
    root = data_dir / "learning"
    instincts = root / "instincts"
    evolved = root / "evolved"
    team_experience = root / "team-experience"
    return LearningPaths(
        root=root,
        observations_file=root / "observations.jsonl",
        instincts_personal_dir=instincts / "personal",
        instincts_inherited_dir=instincts / "inherited",
        evolved_skills_dir=evolved / "skills",
        evolved_commands_dir=evolved / "commands",
        evolved_agents_dir=evolved / "agents",
        team_experience_capsules_dir=team_experience / "capsules",
        team_experience_exports_dir=team_experience / "exports",
        team_experience_feedback_file=team_experience / "feedback.jsonl",
    )


def ensure_learning_dirs(settings: Settings) -> LearningPaths:
    p = get_learning_paths(settings)
    for d in (
        p.root,
        p.instincts_personal_dir,
        p.instincts_inherited_dir,
        p.evolved_skills_dir,
        p.evolved_commands_dir,
        p.evolved_agents_dir,
        p.team_experience_capsules_dir,
        p.team_experience_exports_dir,
    ):
        d.mkdir(parents=True, exist_ok=True)
    return p
