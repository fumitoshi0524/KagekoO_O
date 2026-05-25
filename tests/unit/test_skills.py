import pytest
from pathlib import Path
from kageko.learning.skills import SkillEngine, Skill
from kageko.data.db import KagekoDB


@pytest.fixture
async def db(tmp_path):
    database = KagekoDB(str(tmp_path / "test.db"))
    await database.init()
    yield database
    await database.close()


@pytest.fixture
async def engine(db):
    return SkillEngine(db=db)


def test_skill_parse_from_markdown(tmp_path):
    md_file = tmp_path / "test-skill.md"
    md_file.write_text("""---
name: deploy-check
version: 1.0.0
trigger: When deploying
description: Pre-deployment validation
tags: [devops]
---

# Deploy Check

## Steps
1. Run tests
2. Check git status
""")
    skill = Skill.from_markdown(str(md_file))
    assert skill.name == "deploy-check"
    assert skill.version == "1.0.0"
    assert "Run tests" in skill.content


def test_skill_parse_missing_name(tmp_path):
    md_file = tmp_path / "bad.md"
    md_file.write_text("""---
version: 1.0.0
---

No name here
""")
    with pytest.raises(ValueError, match="name"):
        Skill.from_markdown(str(md_file))


def test_skill_to_markdown():
    skill = Skill(
        name="test",
        version="1.0.0",
        trigger="When testing",
        description="A test skill",
        content="# Test\n\n## Steps\n1. Do thing",
        tags=["test"],
    )
    md = skill.to_markdown()
    assert "name: test" in md
    assert "Do thing" in md


@pytest.mark.asyncio
async def test_skill_save_and_search(engine, db):
    skill = Skill(
        name="deploy-check",
        version="1.0.0",
        trigger="When deploying",
        description="Pre-deployment validation",
        content="# Deploy\n1. Run tests",
        tags=["devops"],
    )
    await engine.save(skill)
    results = await engine.search("deploy")
    assert len(results) == 1
    assert results[0].name == "deploy-check"
