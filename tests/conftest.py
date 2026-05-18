from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from qaoa.skills.registry import SkillRegistry
from qaoa.tools.registry import ToolRegistry
from qaoa.types import SkillSpec


@pytest.fixture
def sample_skill() -> SkillSpec:
    return SkillSpec(
        name="test-skill",
        description="A test skill for unit testing",
        instructions="1. Read the file\n2. Write the output\n3. Report results",
        allowed_tools=["file.read", "file.write", "bash.run"],
        permissions=["read", "write"],
        metadata={"category": "operations", "domain": "technology", "tags": ["test"]},
        format="qaoa-uni-tool-call",
    )


@pytest.fixture
def skill_registry() -> SkillRegistry:
    return SkillRegistry()


@pytest.fixture
def tool_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register("echo", lambda p: p,
                 description="Echo back input",
                 category="system", domain="technology")
    reg.register("file.read", lambda p: f"content of {p}",
                 description="Read a file",
                 category="search", domain="technology")
    reg.register("file.write", lambda p: f"wrote {p}",
                 description="Write a file",
                 category="operations", domain="technology")
    reg.register("bash.run", lambda p: f"ran {p}",
                 description="Run a shell command",
                 category="operations", domain="technology")
    reg.freeze()
    return reg


@pytest.fixture
def temp_skills_dir() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)
