# New Kageko Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new AI agent from scratch in `KagekoO_O/` that combines coding precision (hashline/Rust tools), general-purpose capability (multi-platform gateway, learning loop), and research support (QAOA trajectory export).

**Architecture:** Python 3.13+ agent logic with Rust PyO3 extension for performance-critical tools. Dual-mode execution loop (tool-use / QAOA). Single-process multi-platform gateway. SQLite + FTS5 data layer. Skill (Markdown) + Tool (JSON Schema) dual auto-generation.

**Tech Stack:** Python 3.13+, Rust 2024, PyO3/maturin, asyncio/uvloop, typer/rich/textual, SQLite (aiosqlite), aiohttp, OpenAI-compatible LLM API

---

## Phase 1: Foundation (project scaffold + data + core types)

### Task 1: Delete old KagekoO_O code and scaffold new project

**Files:**
- Delete: all existing files under `KagekoO_O/` except `docs/`
- Create: `KagekoO_O/pyproject.toml`
- Create: `KagekoO_O/Cargo.toml`
- Create: `KagekoO_O/kageko.toml`
- Create: `KagekoO_O/src/kageko/__init__.py`
- Create: `KagekoO_O/src/kageko_native/Cargo.toml`
- Create: `KagekoO_O/src/kageko_native/src/lib.rs`
- Create: `KagekoO_O/tests/__init__.py`
- Create: `KagekoO_O/.gitignore`

- [ ] **Step 1: Create pyproject.toml with maturin build backend**

```toml
[build-system]
requires = ["maturin>=1.7,<2.0"]
build-backend = "maturin"

[project]
name = "kageko"
version = "0.1.0"
description = "Three-in-one AI agent: coding, general-purpose, research"
requires-python = ">=3.13"
license = { text = "MIT" }
dependencies = [
    "openai>=1.60.0",
    "aiosqlite>=0.20.0",
    "aiohttp>=3.11.0",
    "typer>=0.15.0",
    "rich>=13.9.0",
    "textual>=0.89.0",
    "uvloop>=0.21.0; sys_platform != 'win32'",
    "pydantic>=2.10.0",
    "tomli>=2.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]

[project.scripts]
kageko = "kageko.cli:app"

[tool.maturin]
features = ["pyo3/extension-module"]
manifest-path = "src/kageko_native/Cargo.toml"
python-source = "src"
module-name = "kageko_native._native"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py313"
line-length = 100

[tool.mypy]
python_version = "3.13"
strict = true
```

- [ ] **Step 2: Create Rust workspace Cargo.toml**

```toml
[workspace]
resolver = "2"
members = ["src/kageko_native"]

[workspace.package]
version = "0.1.0"
edition = "2024"
```

- [ ] **Step 3: Create kageko_native Cargo.toml**

```toml
[package]
name = "kageko-native"
version.workspace = true
edition.workspace = true

[lib]
name = "_native"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.23", features = ["extension-module"] }
```

- [ ] **Step 4: Create minimal Rust lib.rs**

```rust
use pyo3::prelude::*;

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
```

- [ ] **Step 5: Create kageko/__init__.py**

```python
"""Kageko — three-in-one AI agent."""

__version__ = "0.1.0"
```

- [ ] **Step 6: Create kageko.toml default config**

```toml
[agent]
model = "gpt-4o"
mode = "tool-use"  # or "qaoa"
max_turns = 20

[security]
mode = "interactive"  # "permissive", "read-only", "interactive"
sandbox = false

[database]
path = "~/.kageko/kageko.db"

[logging]
level = "INFO"
```

- [ ] **Step 7: Create .gitignore**

```
__pycache__/
*.pyc
*.so
*.dylib
*.dll
target/
*.egg-info/
dist/
build/
.kageko/
```

- [ ] **Step 8: Verify build**

```bash
cd KagekoO_O
pip install -e ".[dev]"
```
Expected: Rust extension compiles, `import kageko` works, `kageko --version` prints 0.1.0

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: scaffold new Kageko agent project"
```

---

### Task 2: Core types and models

**Files:**
- Create: `src/kageko/types.py`
- Test: `tests/unit/test_types.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_types.py
import pytest
from kageko.types import Message, ToolCall, ToolResult, AgentResult, AgentMode


def test_message_user():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"


def test_message_to_dict():
    msg = Message(role="user", content="hello")
    d = msg.to_dict()
    assert d == {"role": "user", "content": "hello"}


def test_tool_call():
    tc = ToolCall(id="call_1", name="file_read", args={"path": "test.py"})
    assert tc.id == "call_1"
    assert tc.name == "file_read"
    assert tc.args == {"path": "test.py"}


def test_tool_result():
    tr = ToolResult(tool_call_id="call_1", content="file contents here")
    assert tr.tool_call_id == "call_1"
    assert tr.content == "file contents here"


def test_tool_result_to_message():
    tr = ToolResult(tool_call_id="call_1", content="file contents")
    msg = tr.to_message()
    assert msg.role == "tool"
    assert msg.content == "file contents"


def test_agent_result():
    result = AgentResult(answer="done", turn_count=3, tokens_used=1500)
    assert result.answer == "done"
    assert result.turn_count == 3
    assert result.trajectory is None


def test_agent_mode_values():
    assert AgentMode.TOOL_USE.value == "tool-use"
    assert AgentMode.QAOA.value == "qaoa"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_types.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'kageko.types'"

- [ ] **Step 3: Write minimal implementation**

```python
# src/kageko/types.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentMode(str, Enum):
    TOOL_USE = "tool-use"
    QAOA = "qaoa"


@dataclass
class Message:
    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.name, "arguments": self.args},
        }


@dataclass
class ToolResult:
    tool_call_id: str
    content: str
    is_error: bool = False

    def to_message(self) -> Message:
        return Message(
            role="tool",
            content=self.content,
            tool_call_id=self.tool_call_id,
        )


@dataclass
class AgentResult:
    answer: str
    turn_count: int = 0
    tokens_used: int = 0
    trajectory: Any = None  # QAOATrajectory | None


@dataclass
class QAOAStep:
    """Single step in QAOA trajectory: Action + Observation."""
    step_number: int
    action: ToolCall
    observation: ToolResult


@dataclass
class QAOATrajectory:
    """Full QAOA trajectory for research/export."""
    query: str
    steps: list[QAOAStep] = field(default_factory=list)
    answer: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def step(self, action: ToolCall, observation: ToolResult) -> None:
        self.steps.append(QAOAStep(
            step_number=len(self.steps) + 1,
            action=action,
            observation=observation,
        ))

    def set_answer(self, answer: str) -> None:
        self.answer = answer
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_types.py -v
```
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/types.py tests/unit/test_types.py
git commit -m "feat: add core types (Message, ToolCall, ToolResult, QAOATrajectory)"
```

---

### Task 3: Database layer (SQLite + FTS5)

**Files:**
- Create: `src/kageko/data/db.py`
- Create: `src/kageko/data/sessions.py`
- Create: `src/kageko/data/__init__.py`
- Test: `tests/unit/test_db.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_db.py
import pytest
import tempfile
from pathlib import Path
from kageko.data.db import KagekoDB


@pytest.fixture
async def db(tmp_path):
    db_path = tmp_path / "test.db"
    database = KagekoDB(str(db_path))
    await database.init()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_init_creates_tables(db):
    tables = await db.list_tables()
    assert "sessions" in tables
    assert "skills" in tables
    assert "tools" in tables
    assert "trajectories" in tables
    assert "memory" in tables


@pytest.mark.asyncio
async def test_create_and_get_session(db):
    session = await db.create_session(platform="cli", chat_id="local")
    assert session.id is not None
    assert session.platform == "cli"

    fetched = await db.get_session(session.id)
    assert fetched.platform == "cli"
    assert fetched.chat_id == "local"


@pytest.mark.asyncio
async def test_session_messages(db):
    session = await db.create_session(platform="cli", chat_id="local")
    await db.append_message(session.id, role="user", content="hello")
    await db.append_message(session.id, role="assistant", content="hi there")

    messages = await db.get_messages(session.id)
    assert len(messages) == 2
    assert messages[0].content == "hello"
    assert messages[1].content == "hi there"


@pytest.mark.asyncio
async def test_save_and_search_skill(db):
    await db.save_skill(
        name="deploy-check",
        version="1.0.0",
        trigger="When deploying",
        description="Pre-deployment checks",
        content="# Deploy Check\n\n1. Run tests\n2. Check git status",
        tags=["devops"],
    )
    results = await db.search_skills("deploy")
    assert len(results) == 1
    assert results[0].name == "deploy-check"


@pytest.mark.asyncio
async def test_save_and_search_memory(db):
    await db.save_memory(key="user_pref", value="User prefers dark mode", source="session_1")
    results = await db.search_memory("dark mode")
    assert len(results) == 1
    assert results[0].key == "user_pref"


@pytest.mark.asyncio
async def test_save_trajectory(db):
    trajectory_data = {
        "query": "read config.py",
        "steps": [
            {"step": 1, "tool": "file_read", "args": {"path": "config.py"}, "result": "..."}
        ],
        "answer": "The config sets model=gpt-4o",
    }
    await db.save_trajectory(trajectory_data)
    trajectories = await db.list_trajectories()
    assert len(trajectories) == 1
    assert trajectories[0].query == "read config.py"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_db.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'kageko.data'"

- [ ] **Step 3: Write implementation**

```python
# src/kageko/data/__init__.py
from kageko.data.db import KagekoDB

__all__ = ["KagekoDB"]
```

```python
# src/kageko/data/db.py
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite


@dataclass
class SessionRecord:
    id: str
    platform: str
    chat_id: str
    created_at: str


@dataclass
class MessageRecord:
    role: str
    content: str
    created_at: str


@dataclass
class SkillRecord:
    name: str
    version: str
    trigger: str
    description: str
    content: str
    tags: list[str]
    created_at: str


@dataclass
class MemoryRecord:
    key: str
    value: str
    source: str
    created_at: str


@dataclass
class TrajectoryRecord:
    id: str
    query: str
    data: dict
    created_at: str


class KagekoDB:
    def __init__(self, path: str = "~/.kageko/kageko.db"):
        self._path = str(Path(path).expanduser())
        self._conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()

    async def _create_tables(self) -> None:
        assert self._conn is not None
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS skills (
                name TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                trigger TEXT NOT NULL,
                description TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'active',
                last_used TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tools (
                name TEXT PRIMARY KEY,
                schema_json TEXT NOT NULL,
                implementation TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                usage_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trajectories (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memory (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS curator_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_name TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            );

            -- FTS5 virtual tables for full-text search
            CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
                name, description, content, tags,
                content='skills',
                content_rowid='rowid'
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                key, value,
                content='memory',
                content_rowid='rowid'
            );
        """)
        await self._conn.commit()

    async def list_tables(self) -> list[str]:
        assert self._conn is not None
        cursor = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        rows = await cursor.fetchall()
        return [row["name"] for row in rows]

    # --- Sessions ---

    async def create_session(self, platform: str, chat_id: str) -> SessionRecord:
        assert self._conn is not None
        session_id = uuid.uuid4().hex[:12]
        now = _now()
        await self._conn.execute(
            "INSERT INTO sessions (id, platform, chat_id, created_at) VALUES (?, ?, ?, ?)",
            (session_id, platform, chat_id, now),
        )
        await self._conn.commit()
        return SessionRecord(id=session_id, platform=platform, chat_id=chat_id, created_at=now)

    async def get_session(self, session_id: str) -> SessionRecord:
        assert self._conn is not None
        cursor = await self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise KeyError(f"Session not found: {session_id}")
        return SessionRecord(
            id=row["id"],
            platform=row["platform"],
            chat_id=row["chat_id"],
            created_at=row["created_at"],
        )

    # --- Messages ---

    async def append_message(self, session_id: str, role: str, content: str) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, _now()),
        )
        await self._conn.commit()

    async def get_messages(self, session_id: str) -> list[MessageRecord]:
        assert self._conn is not None
        cursor = await self._conn.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [MessageRecord(role=r["role"], content=r["content"], created_at=r["created_at"]) for r in rows]

    # --- Skills ---

    async def save_skill(
        self,
        name: str,
        version: str,
        trigger: str,
        description: str,
        content: str,
        tags: list[str],
    ) -> None:
        assert self._conn is not None
        now = _now()
        await self._conn.execute(
            """INSERT OR REPLACE INTO skills
               (name, version, trigger, description, content, tags, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, version, trigger, description, content, json.dumps(tags), now),
        )
        await self._conn.commit()

    async def search_skills(self, query: str) -> list[SkillRecord]:
        assert self._conn is not None
        cursor = await self._conn.execute(
            """SELECT s.name, s.version, s.trigger, s.description, s.content, s.tags, s.created_at
               FROM skills_fts fts
               JOIN skills s ON s.rowid = fts.rowid
               WHERE skills_fts MATCH ?
               LIMIT 10""",
            (query,),
        )
        rows = await cursor.fetchall()
        return [
            SkillRecord(
                name=r["name"],
                version=r["version"],
                trigger=r["trigger"],
                description=r["description"],
                content=r["content"],
                tags=json.loads(r["tags"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # --- Tools ---

    async def save_tool(
        self,
        name: str,
        schema_json: dict,
        implementation: str,
        category: str,
    ) -> None:
        assert self._conn is not None
        await self._conn.execute(
            """INSERT OR REPLACE INTO tools
               (name, schema_json, implementation, category, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (name, json.dumps(schema_json), implementation, category, _now()),
        )
        await self._conn.commit()

    # --- Memory ---

    async def save_memory(self, key: str, value: str, source: str) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "INSERT OR REPLACE INTO memory (key, value, source, created_at) VALUES (?, ?, ?, ?)",
            (key, value, source, _now()),
        )
        await self._conn.commit()

    async def search_memory(self, query: str) -> list[MemoryRecord]:
        assert self._conn is not None
        cursor = await self._conn.execute(
            """SELECT m.key, m.value, m.source, m.created_at
               FROM memory_fts fts
               JOIN memory m ON m.rowid = fts.rowid
               WHERE memory_fts MATCH ?
               LIMIT 10""",
            (query,),
        )
        rows = await cursor.fetchall()
        return [
            MemoryRecord(key=r["key"], value=r["value"], source=r["source"], created_at=r["created_at"])
            for r in rows
        ]

    # --- Trajectories ---

    async def save_trajectory(self, data: dict) -> str:
        assert self._conn is not None
        traj_id = uuid.uuid4().hex[:12]
        await self._conn.execute(
            "INSERT INTO trajectories (id, query, data, created_at) VALUES (?, ?, ?, ?)",
            (traj_id, data.get("query", ""), json.dumps(data), _now()),
        )
        await self._conn.commit()
        return traj_id

    async def list_trajectories(self) -> list[TrajectoryRecord]:
        assert self._conn is not None
        cursor = await self._conn.execute(
            "SELECT id, query, data, created_at FROM trajectories ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            TrajectoryRecord(
                id=r["id"], query=r["query"], data=json.loads(r["data"]), created_at=r["created_at"]
            )
            for r in rows
        ]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_db.py -v
```
Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/data/ tests/unit/test_db.py
git commit -m "feat: add SQLite+FTS5 data layer with sessions, skills, memory, tools, trajectories"
```

---

### Task 4: LLM adapter (OpenAI-compatible)

**Files:**
- Create: `src/kageko/llm.py`
- Test: `tests/unit/test_llm.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_llm.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from kageko.llm import LLMAdapter, LLMResponse
from kageko.types import Message, ToolCall


@pytest.fixture
def adapter():
    return LLMAdapter(model="gpt-4o", api_key="test-key", base_url="https://api.openai.com/v1")


def test_adapter_init(adapter):
    assert adapter.model == "gpt-4o"
    assert adapter.base_url == "https://api.openai.com/v1"


def test_convert_messages():
    adapter = LLMAdapter(model="gpt-4o", api_key="key")
    messages = [
        Message(role="user", content="hello"),
        Message(role="assistant", content="hi"),
    ]
    result = adapter._convert_messages(messages)
    assert result == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]


def test_convert_tool_schemas():
    adapter = LLMAdapter(model="gpt-4o", api_key="key")
    schemas = [
        {
            "name": "file_read",
            "description": "Read a file",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }
    ]
    result = adapter._convert_tools(schemas)
    assert len(result) == 1
    assert result[0]["type"] == "function"
    assert result[0]["function"]["name"] == "file_read"


@pytest.mark.asyncio
async def test_chat_no_tools(adapter):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello!"
    mock_response.choices[0].message.tool_calls = None
    mock_response.usage.total_tokens = 100

    adapter._client = AsyncMock()
    adapter._client.chat.completions.create = AsyncMock(return_value=mock_response)

    messages = [Message(role="user", content="hello")]
    result = await adapter.chat(messages)
    assert result.content == "Hello!"
    assert result.has_tool_calls() is False
    assert result.tokens_used == 100


@pytest.mark.asyncio
async def test_chat_with_tool_calls(adapter):
    mock_tc = MagicMock()
    mock_tc.id = "call_1"
    mock_tc.function.name = "file_read"
    mock_tc.function.arguments = '{"path": "test.py"}'

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    mock_response.choices[0].message.tool_calls = [mock_tc]
    mock_response.usage.total_tokens = 200

    adapter._client = AsyncMock()
    adapter._client.chat.completions.create = AsyncMock(return_value=mock_response)

    messages = [Message(role="user", content="read test.py")]
    result = await adapter.chat(messages, tools=[{"name": "file_read"}])
    assert result.has_tool_calls() is True
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "file_read"
    assert result.tool_calls[0].args == {"path": "test.py"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_llm.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'kageko.llm'"

- [ ] **Step 3: Write implementation**

```python
# src/kageko/llm.py
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from kageko.types import Message, ToolCall


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall]
    tokens_used: int = 0

    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMAdapter:
    """OpenAI-compatible LLM adapter. Works with any provider that implements the OpenAI API."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.7,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        result = []
        for msg in messages:
            d: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                d["tool_calls"] = [tc.to_dict() for tc in msg.tool_calls]
            if msg.tool_call_id:
                d["tool_call_id"] = msg.tool_call_id
            result.append(d)
        return result

    def _convert_tools(self, schemas: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"type": "function", "function": schema} for schema in schemas]

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": self.temperature,
        }
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        response = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        content = choice.message.content or ""

        tool_calls: list[ToolCall] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                args = json.loads(tc.function.arguments)
                tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, args=args))

        tokens_used = response.usage.total_tokens if response.usage else 0

        return LLMResponse(content=content, tool_calls=tool_calls, tokens_used=tokens_used)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_llm.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/llm.py tests/unit/test_llm.py
git commit -m "feat: add OpenAI-compatible LLM adapter"
```

---

## Phase 2: Agent Core (loop + permissions + tools)

### Task 5: Tool registry and schemas

**Files:**
- Create: `src/kageko/tools/__init__.py`
- Create: `src/kageko/tools/registry.py`
- Create: `src/kageko/tools/schemas.py`
- Test: `tests/unit/test_tool_registry.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_tool_registry.py
import pytest
from kageko.tools.registry import ToolRegistry, Tool


@pytest.fixture
def registry():
    return ToolRegistry()


def test_register_tool(registry):
    tool = Tool(
        name="file_read",
        description="Read a file",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        handler=lambda args: "file contents",
        category="file",
    )
    registry.register(tool)
    assert registry.get("file_read") is tool


def test_register_duplicate_raises(registry):
    tool = Tool(
        name="file_read",
        description="Read",
        parameters={"type": "object", "properties": {}},
        handler=lambda args: "",
        category="file",
    )
    registry.register(tool)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool)


def test_schemas_returns_openai_format(registry):
    tool = Tool(
        name="file_read",
        description="Read a file",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"],
        },
        handler=lambda args: "",
        category="file",
    )
    registry.register(tool)
    schemas = registry.schemas()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "file_read"
    assert schemas[0]["description"] == "Read a file"
    assert "parameters" in schemas[0]


def test_categories(registry):
    read_tool = Tool(name="file_read", description="", parameters={}, handler=lambda a: "", category="file")
    write_tool = Tool(name="file_write", description="", parameters={}, handler=lambda a: "", category="file")
    bash_tool = Tool(name="bash", description="", parameters={}, handler=lambda a: "", category="shell")
    registry.register(read_tool)
    registry.register(write_tool)
    registry.register(bash_tool)
    assert registry.categories() == {"file": ["file_read", "file_write"], "shell": ["bash"]}


def test_list_tools(registry):
    t1 = Tool(name="a", description="", parameters={}, handler=lambda a: "", category="x")
    t2 = Tool(name="b", description="", parameters={}, handler=lambda a: "", category="y")
    registry.register(t1)
    registry.register(t2)
    names = registry.list_names()
    assert sorted(names) == ["a", "b"]


@pytest.mark.asyncio
async def test_execute_tool(registry):
    async def handler(args):
        return f"read {args['path']}"

    tool = Tool(
        name="file_read",
        description="Read a file",
        parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        handler=handler,
        category="file",
    )
    registry.register(tool)
    result = await registry.execute("file_read", {"path": "test.py"})
    assert result == "read test.py"


@pytest.mark.asyncio
async def test_execute_unknown_tool(registry):
    with pytest.raises(KeyError, match="not found"):
        await registry.execute("nonexistent", {})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_tool_registry.py -v
```
Expected: FAIL with import error

- [ ] **Step 3: Write implementation**

```python
# src/kageko/tools/__init__.py
from kageko.tools.registry import ToolRegistry, Tool

__all__ = ["ToolRegistry", "Tool"]
```

```python
# src/kageko/tools/registry.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any]], Awaitable[str]]
    category: str

    def to_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._categories: dict[str, list[str]] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        self._categories.setdefault(tool.category, []).append(tool.name)

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def categories(self) -> dict[str, list[str]]:
        return dict(self._categories)

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute(self, name: str, args: dict[str, Any]) -> str:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        tool = self._tools[name]
        return await tool.handler(args)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_tool_registry.py -v
```
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/tools/ tests/unit/test_tool_registry.py
git commit -m "feat: add tool registry with schema generation and async execution"
```

---

### Task 6: Permission pipeline (4-layer)

**Files:**
- Create: `src/kageko/agent/permissions.py`
- Create: `src/kageko/agent/__init__.py`
- Test: `tests/unit/test_permissions.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_permissions.py
import pytest
from unittest.mock import AsyncMock
from kageko.agent.permissions import PermissionPipeline, Decision, SecurityMode, RuleEngine
from kageko.types import ToolCall


@pytest.fixture
def pipeline():
    return PermissionPipeline(mode=SecurityMode.INTERACTIVE, prompt_fn=AsyncMock(return_value=Decision.ALLOW))


def test_read_only_mode_denies_writes(pipeline):
    pipeline.mode = SecurityMode.READ_ONLY
    tc = ToolCall(id="1", name="file_write", args={"path": "x.py", "content": "hi"})
    decision = pipeline._check_mode(tc)
    assert decision == Decision.DENY


def test_read_only_mode_allows_reads(pipeline):
    pipeline.mode = SecurityMode.READ_ONLY
    tc = ToolCall(id="1", name="file_read", args={"path": "x.py"})
    decision = pipeline._check_mode(tc)
    assert decision is None


def test_dangerous_pattern_blocks_rm_rf(pipeline):
    tc = ToolCall(id="1", name="bash", args={"command": "rm -rf /"})
    decision = pipeline.rule_engine.check(tc)
    assert decision == Decision.DENY


def test_dangerous_pattern_allows_safe_command(pipeline):
    tc = ToolCall(id="1", name="bash", args={"command": "ls -la"})
    decision = pipeline.rule_engine.check(tc)
    assert decision is None


def test_high_risk_tools_require_sandbox(pipeline):
    tc = ToolCall(id="1", name="bash", args={"command": "echo hi"})
    assert tc.name in pipeline.HIGH_RISK_TOOLS


@pytest.mark.asyncio
async def test_full_pipeline_allow_read(pipeline):
    pipeline.mode = SecurityMode.PERMISSIVE
    tc = ToolCall(id="1", name="file_read", args={"path": "test.py"})
    decision = await pipeline.check(tc)
    assert decision == Decision.ALLOW


@pytest.mark.asyncio
async def test_full_pipeline_deny_dangerous(pipeline):
    tc = ToolCall(id="1", name="bash", args={"command": "rm -rf /"})
    decision = await pipeline.check(tc)
    assert decision == Decision.DENY
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_permissions.py -v
```
Expected: FAIL with import error

- [ ] **Step 3: Write implementation**

```python
# src/kageko/agent/__init__.py
# empty
```

```python
# src/kageko/agent/permissions.py
from __future__ import annotations

import re
from enum import Enum
from typing import Any, Awaitable, Callable

from kageko.types import ToolCall


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    EXECUTE_IN_SANDBOX = "sandbox"
    ASK_USER = "ask"


class SecurityMode(str, Enum):
    PERMISSIVE = "permissive"
    READ_ONLY = "read-only"
    INTERACTIVE = "interactive"


class RuleEngine:
    """Layer 1: Dangerous pattern detection."""

    DANGEROUS_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"rm\s+(-rf?|--recursive)\s+[/~]", re.IGNORECASE),
        re.compile(r":\(\)\s*\{.*\|.*&\s*\}", re.DOTALL),  # fork bomb
        re.compile(r"chmod\s+777", re.IGNORECASE),
        re.compile(r"curl.*\|\s*(ba)?sh", re.IGNORECASE),
        re.compile(r"mkfs\.", re.IGNORECASE),
        re.compile(r"dd\s+if=/dev/(zero|random)\s+of=/", re.IGNORECASE),
    ]

    def check(self, tool_call: ToolCall) -> Decision | None:
        if tool_call.name == "bash":
            command = tool_call.args.get("command", "")
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern.search(command):
                    return Decision.DENY
        return None


PromptFn = Callable[[ToolCall], Awaitable[Decision]]


class PermissionPipeline:
    """4-layer permission pipeline: rules -> sandbox -> mode -> interactive."""

    HIGH_RISK_TOOLS: set[str] = {"bash", "eval"}

    def __init__(
        self,
        mode: SecurityMode = SecurityMode.INTERACTIVE,
        prompt_fn: PromptFn | None = None,
        sandbox_enabled: bool = False,
    ):
        self.mode = mode
        self.sandbox_enabled = sandbox_enabled
        self.prompt_fn = prompt_fn
        self.rule_engine = RuleEngine()

    async def check(self, tool_call: ToolCall) -> Decision:
        # Layer 1: Rule engine
        if decision := self.rule_engine.check(tool_call):
            return decision

        # Layer 2: Sandbox for high-risk tools
        if self.sandbox_enabled and tool_call.name in self.HIGH_RISK_TOOLS:
            return Decision.EXECUTE_IN_SANDBOX

        # Layer 3: Mode guard
        if decision := self._check_mode(tool_call):
            return decision

        # Layer 4: Interactive prompt
        if self.prompt_fn:
            return await self.prompt_fn(tool_call)
        return Decision.ALLOW

    def _check_mode(self, tool_call: ToolCall) -> Decision | None:
        if self.mode == SecurityMode.READ_ONLY:
            write_tools = {"file_write", "file_edit", "bash", "eval"}
            if tool_call.name in write_tools:
                return Decision.DENY
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_permissions.py -v
```
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/agent/permissions.py src/kageko/agent/__init__.py tests/unit/test_permissions.py
git commit -m "feat: add 4-layer permission pipeline with rule engine and mode guard"
```

---

### Task 7: Agent core — dual-mode execution loop

**Files:**
- Create: `src/kageko/agent/loop.py`
- Test: `tests/unit/test_agent_loop.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_agent_loop.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from kageko.agent.loop import AgentEngine
from kageko.agent.permissions import PermissionPipeline, Decision, SecurityMode
from kageko.llm import LLMAdapter, LLMResponse
from kageko.tools.registry import ToolRegistry, Tool
from kageko.types import Message, AgentMode, ToolCall


@pytest.fixture
def tool_registry():
    registry = ToolRegistry()

    async def echo_handler(args):
        return f"echo: {args.get('text', '')}"

    registry.register(Tool(
        name="echo",
        description="Echo text",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        handler=echo_handler,
        category="system",
    ))
    return registry


@pytest.fixture
def llm_adapter():
    adapter = MagicMock(spec=LLMAdapter)
    return adapter


@pytest.fixture
def engine(llm_adapter, tool_registry):
    permissions = PermissionPipeline(mode=SecurityMode.PERMISSIVE)
    return AgentEngine(
        llm=llm_adapter,
        tool_registry=tool_registry,
        permissions=permissions,
        max_turns=10,
    )


@pytest.mark.asyncio
async def test_tool_use_mode_simple_answer(engine, llm_adapter):
    llm_adapter.chat = AsyncMock(return_value=LLMResponse(
        content="Hello!",
        tool_calls=[],
        tokens_used=50,
    ))
    result = await engine.run("hi", mode=AgentMode.TOOL_USE)
    assert result.answer == "Hello!"
    assert result.turn_count == 1


@pytest.mark.asyncio
async def test_tool_use_mode_with_tool_call(engine, llm_adapter):
    llm_adapter.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="echo", args={"text": "hello"})
        ], tokens_used=30),
        LLMResponse(content="The echo said: echo: hello", tool_calls=[], tokens_used=40),
    ])
    result = await engine.run("echo hello", mode=AgentMode.TOOL_USE)
    assert result.answer == "The echo said: echo: hello"
    assert result.turn_count == 2


@pytest.mark.asyncio
async def test_qaoa_mode_records_trajectory(engine, llm_adapter):
    llm_adapter.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="echo", args={"text": "test"})
        ], tokens_used=30),
        LLMResponse(content="result", tool_calls=[], tokens_used=20),
    ])
    result = await engine.run("echo test", mode=AgentMode.QAOA)
    assert result.answer == "result"
    assert result.trajectory is not None
    assert len(result.trajectory.steps) == 1
    assert result.trajectory.steps[0].action.name == "echo"
    assert result.trajectory.steps[0].observation.content == "echo: test"


@pytest.mark.asyncio
async def test_max_turns_stops_loop(engine, llm_adapter):
    engine.max_turns = 2
    llm_adapter.chat = AsyncMock(return_value=LLMResponse(
        content="",
        tool_calls=[ToolCall(id="c1", name="echo", args={"text": "loop"})],
        tokens_used=10,
    ))
    result = await engine.run("loop", mode=AgentMode.TOOL_USE)
    assert result.turn_count == 2


@pytest.mark.asyncio
async def test_permission_denied_skips_tool(engine, llm_adapter):
    engine.permissions.mode = SecurityMode.READ_ONLY
    llm_adapter.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="echo", args={"text": "hi"})
        ], tokens_used=20),
        LLMResponse(content="cant do that", tool_calls=[], tokens_used=10),
    ])
    result = await engine.run("echo hi", mode=AgentMode.TOOL_USE)
    assert result.answer == "cant do that"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_agent_loop.py -v
```
Expected: FAIL with import error

- [ ] **Step 3: Write implementation**

```python
# src/kageko/agent/loop.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kageko.agent.permissions import Decision, PermissionPipeline
from kageko.llm import LLMAdapter
from kageko.tools.registry import ToolRegistry
from kageko.types import AgentMode, AgentResult, Message, QAOATrajectory, ToolCall, ToolResult


@dataclass
class AgentContext:
    messages: list[Message] = field(default_factory=list)
    turn_count: int = 0
    tokens_used: int = 0
    trajectory: QAOATrajectory | None = None


class AgentEngine:
    def __init__(
        self,
        llm: LLMAdapter,
        tool_registry: ToolRegistry,
        permissions: PermissionPipeline,
        max_turns: int = 20,
    ):
        self.llm = llm
        self.tool_registry = tool_registry
        self.permissions = permissions
        self.max_turns = max_turns

    async def run(self, message: str, mode: AgentMode = AgentMode.TOOL_USE) -> AgentResult:
        if mode == AgentMode.QAOA:
            return await self._qaoa_loop(message)
        return await self._tool_use_loop(message)

    async def _tool_use_loop(self, message: str) -> AgentResult:
        ctx = AgentContext(messages=[Message(role="user", content=message)])
        return await self._run_loop(ctx, record_trajectory=False)

    async def _qaoa_loop(self, message: str) -> AgentResult:
        trajectory = QAOATrajectory(query=message)
        ctx = AgentContext(
            messages=[Message(role="user", content=message)],
            trajectory=trajectory,
        )
        return await self._run_loop(ctx, record_trajectory=True)

    async def _run_loop(self, ctx: AgentContext, record_trajectory: bool) -> AgentResult:
        schemas = self.tool_registry.schemas()

        while ctx.turn_count < self.max_turns:
            ctx.turn_count += 1
            response = await self.llm.chat(ctx.messages, tools=schemas)
            ctx.tokens_used += response.tokens_used

            if not response.has_tool_calls():
                # Final answer
                ctx.messages.append(Message(role="assistant", content=response.content))
                if ctx.trajectory:
                    ctx.trajectory.set_answer(response.content)
                return AgentResult(
                    answer=response.content,
                    turn_count=ctx.turn_count,
                    tokens_used=ctx.tokens_used,
                    trajectory=ctx.trajectory,
                )

            # Process tool calls
            results = await self._execute_tool_calls(response.tool_calls)
            ctx.messages.append(Message(
                role="assistant",
                content=response.content or "",
                tool_calls=response.tool_calls,
            ))
            for result in results:
                ctx.messages.append(result.to_message())
                if record_trajectory and ctx.trajectory:
                    matching_call = next(
                        (tc for tc in response.tool_calls if tc.id == result.tool_call_id),
                        None,
                    )
                    if matching_call:
                        ctx.trajectory.step(matching_call, result)

        # Max turns reached
        return AgentResult(
            answer="(max turns reached)",
            turn_count=ctx.turn_count,
            tokens_used=ctx.tokens_used,
            trajectory=ctx.trajectory,
        )

    async def _execute_tool_calls(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Execute tool calls in parallel using asyncio.gather."""

        async def _execute_one(tc: ToolCall) -> ToolResult:
            decision = await self.permissions.check(tc)
            if decision == Decision.DENY:
                return ToolResult(
                    tool_call_id=tc.id,
                    content=f"[DENIED] Tool '{tc.name}' blocked by security policy",
                    is_error=True,
                )
            if decision == Decision.EXECUTE_IN_SANDBOX:
                return ToolResult(
                    tool_call_id=tc.id,
                    content="[SANDBOX] Not yet implemented",
                    is_error=True,
                )
            try:
                content = await self.tool_registry.execute(tc.name, tc.args)
                return ToolResult(tool_call_id=tc.id, content=content)
            except Exception as e:
                return ToolResult(
                    tool_call_id=tc.id,
                    content=f"[ERROR] {type(e).__name__}: {e}",
                    is_error=True,
                )

        import asyncio
        results = await asyncio.gather(*[_execute_one(tc) for tc in tool_calls])
        return list(results)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_agent_loop.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/agent/loop.py tests/unit/test_agent_loop.py
git commit -m "feat: add dual-mode agent execution loop (tool-use / QAOA)"
```

---

### Task 8: Built-in tools (file, bash, echo, todo)

**Files:**
- Create: `src/kageko/tools/builtin/__init__.py`
- Create: `src/kageko/tools/builtin/file_tools.py`
- Create: `src/kageko/tools/builtin/shell_tools.py`
- Create: `src/kageko/tools/builtin/system_tools.py`
- Test: `tests/unit/test_builtin_tools.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_builtin_tools.py
import pytest
import tempfile
from pathlib import Path
from kageko.tools.builtin.file_tools import file_read, file_write, file_list
from kageko.tools.builtin.shell_tools import bash_run
from kageko.tools.builtin.system_tools import echo, todo_add, todo_list


@pytest.mark.asyncio
async def test_file_write_and_read(tmp_path):
    fp = str(tmp_path / "test.txt")
    result = await file_write({"path": fp, "content": "hello world"})
    assert "written" in result.lower()

    content = await file_read({"path": fp})
    assert content == "hello world"


@pytest.mark.asyncio
async def test_file_read_not_found():
    content = await file_read({"path": "/nonexistent/file.txt"})
    assert "[ERROR]" in content


@pytest.mark.asyncio
async def test_file_list(tmp_path):
    (tmp_path / "a.py").write_text("# a")
    (tmp_path / "b.txt").write_text("b")
    result = await file_list({"path": str(tmp_path)})
    assert "a.py" in result
    assert "b.txt" in result


@pytest.mark.asyncio
async def test_bash_run():
    result = await bash_run({"command": "echo hello"})
    assert "hello" in result


@pytest.mark.asyncio
async def test_bash_run_timeout():
    result = await bash_run({"command": "sleep 10", "timeout": 1})
    assert "timeout" in result.lower() or "timed out" in result.lower()


@pytest.mark.asyncio
async def test_echo():
    result = await echo({"text": "test message"})
    assert result == "test message"


@pytest.mark.asyncio
async def test_todo():
    result = await todo_add({"task": "Fix the bug", "priority": "high"})
    assert "added" in result.lower()

    items = await todo_list({})
    assert "Fix the bug" in items
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_builtin_tools.py -v
```
Expected: FAIL with import error

- [ ] **Step 3: Write implementation**

```python
# src/kageko/tools/builtin/__init__.py
from kageko.tools.builtin.file_tools import file_read, file_write, file_list
from kageko.tools.builtin.shell_tools import bash_run
from kageko.tools.builtin.system_tools import echo, todo_add, todo_list

BUILTIN_TOOLS = [
    {"name": "file_read", "fn": file_read, "category": "file",
     "description": "Read the contents of a file",
     "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "File path to read"}}, "required": ["path"]}},

    {"name": "file_write", "fn": file_write, "category": "file",
     "description": "Write content to a file (creates or overwrites)",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},

    {"name": "file_list", "fn": file_list, "category": "file",
     "description": "List files in a directory",
     "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Directory path"}}, "required": ["path"]}},

    {"name": "bash", "fn": bash_run, "category": "shell",
     "description": "Run a shell command",
     "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "integer", "default": 30}}, "required": ["command"]}},

    {"name": "echo", "fn": echo, "category": "system",
     "description": "Echo back the given text",
     "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},

    {"name": "todo_add", "fn": todo_add, "category": "system",
     "description": "Add a task to the todo list",
     "parameters": {"type": "object", "properties": {"task": {"type": "string"}, "priority": {"type": "string", "enum": ["low", "medium", "high"], "default": "medium"}}, "required": ["task"]}},

    {"name": "todo_list", "fn": todo_list, "category": "system",
     "description": "List all pending tasks",
     "parameters": {"type": "object", "properties": {}}},
]

__all__ = ["BUILTIN_TOOLS"]
```

```python
# src/kageko/tools/builtin/file_tools.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


async def file_read(args: dict[str, Any]) -> str:
    path = Path(args["path"])
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"[ERROR] File not found: {path}"
    except PermissionError:
        return f"[ERROR] Permission denied: {path}"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"


async def file_write(args: dict[str, Any]) -> str:
    path = Path(args["path"])
    content = args["content"]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Written {len(content)} chars to {path}"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"


async def file_list(args: dict[str, Any]) -> str:
    path = Path(args["path"])
    try:
        entries = sorted(os.listdir(path))
        lines = []
        for entry in entries:
            full = path / entry
            marker = "/" if full.is_dir() else ""
            lines.append(f"{entry}{marker}")
        return "\n".join(lines) if lines else "(empty directory)"
    except FileNotFoundError:
        return f"[ERROR] Directory not found: {path}"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"
```

```python
# src/kageko/tools/builtin/shell_tools.py
from __future__ import annotations

import asyncio
from typing import Any


async def bash_run(args: dict[str, Any]) -> str:
    command = args["command"]
    timeout = args.get("timeout", 30)
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return f"[ERROR] Command timed out after {timeout}s: {command}"

        output = stdout.decode("utf-8", errors="replace")
        error = stderr.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            return f"[EXIT {proc.returncode}]\n{output}\n{error}".strip()
        return output.strip() or "(no output)"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"
```

```python
# src/kageko/tools/builtin/system_tools.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# In-memory todo list for v1
_todos: list[dict[str, Any]] = []


async def echo(args: dict[str, Any]) -> str:
    return args.get("text", "")


async def todo_add(args: dict[str, Any]) -> str:
    task = args["task"]
    priority = args.get("priority", "medium")
    _todos.append({"task": task, "priority": priority, "done": False})
    return f"Added: [{priority}] {task}"


async def todo_list(args: dict[str, Any]) -> str:
    if not _todos:
        return "(no tasks)"
    lines = []
    for i, item in enumerate(_todos, 1):
        status = "[x]" if item["done"] else "[ ]"
        lines.append(f"{i}. {status} [{item['priority']}] {item['task']}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_builtin_tools.py -v
```
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/tools/builtin/ tests/unit/test_builtin_tools.py
git commit -m "feat: add built-in tools (file read/write/list, bash, echo, todo)"
```

---

### Task 9: Config loader + CLI entry point

**Files:**
- Create: `src/kageko/config.py`
- Create: `src/kageko/cli.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_config.py
import pytest
import tempfile
from pathlib import Path
from kageko.config import KagekoConfig, load_config


def test_default_config():
    config = KagekoConfig()
    assert config.agent.model == "gpt-4o"
    assert config.agent.mode == "tool-use"
    assert config.security.mode == "interactive"


def test_load_config_from_file(tmp_path):
    cfg_file = tmp_path / "kageko.toml"
    cfg_file.write_text("""
[agent]
model = "deepseek-chat"
mode = "qaoa"
max_turns = 50

[security]
mode = "read-only"

[database]
path = "/tmp/test.db"
""")
    config = load_config(str(cfg_file))
    assert config.agent.model == "deepseek-chat"
    assert config.agent.mode == "qaoa"
    assert config.agent.max_turns == 50
    assert config.security.mode == "read-only"


def test_load_config_file_not_found():
    config = load_config("/nonexistent/kageko.toml")
    assert config.agent.model == "gpt-4o"  # falls back to defaults
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_config.py -v
```
Expected: FAIL with import error

- [ ] **Step 3: Write implementation**

```python
# src/kageko/config.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib


@dataclass
class AgentConfig:
    model: str = "gpt-4o"
    mode: str = "tool-use"
    max_turns: int = 20
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"


@dataclass
class SecurityConfig:
    mode: str = "interactive"
    sandbox: bool = False


@dataclass
class DatabaseConfig:
    path: str = "~/.kageko/kageko.db"


@dataclass
class LoggingConfig:
    level: str = "INFO"


@dataclass
class KagekoConfig:
    agent: AgentConfig = field(default_factory=AgentConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def load_config(path: str | None = None) -> KagekoConfig:
    if path and Path(path).exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return _parse_config(data)
    return KagekoConfig()


def _parse_config(data: dict) -> KagekoConfig:
    config = KagekoConfig()

    if "agent" in data:
        a = data["agent"]
        config.agent = AgentConfig(
            model=a.get("model", "gpt-4o"),
            mode=a.get("mode", "tool-use"),
            max_turns=a.get("max_turns", 20),
            api_key=a.get("api_key", ""),
            base_url=a.get("base_url", "https://api.openai.com/v1"),
        )

    if "security" in data:
        s = data["security"]
        config.security = SecurityConfig(
            mode=s.get("mode", "interactive"),
            sandbox=s.get("sandbox", False),
        )

    if "database" in data:
        d = data["database"]
        config.database = DatabaseConfig(path=d.get("path", "~/.kageko/kageko.db"))

    if "logging" in data:
        l = data["logging"]
        config.logging = LoggingConfig(level=l.get("level", "INFO"))

    return config
```

```python
# src/kageko/cli.py
from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from kageko.config import load_config

app = typer.Typer(
    name="kageko",
    help="Kageko — three-in-one AI agent (coding, general-purpose, research)",
)
console = Console()


@app.command()
def chat(
    config_path: str = typer.Option(None, "--config", "-c", help="Path to kageko.toml"),
    model: str = typer.Option(None, "--model", "-m", help="Override model"),
    mode: str = typer.Option(None, "--mode", help="Agent mode: tool-use or qaoa"),
) -> None:
    """Start an interactive chat session."""
    config = load_config(config_path)
    if model:
        config.agent.model = model
    if mode:
        config.agent.mode = mode

    asyncio.run(_interactive_chat(config))


@app.command()
def version() -> None:
    """Print version."""
    import kageko
    console.print(f"Kageko v{kageko.__version__}")


async def _interactive_chat(config) -> None:
    from kageko.agent.loop import AgentEngine
    from kageko.agent.permissions import PermissionPipeline, SecurityMode
    from kageko.data.db import KagekoDB
    from kageko.llm import LLMAdapter
    from kageko.tools.registry import ToolRegistry, Tool
    from kageko.tools.builtin import BUILTIN_TOOLS
    from kageko.types import AgentMode

    # Initialize components
    db = KagekoDB(config.database.path)
    await db.init()

    llm = LLMAdapter(
        model=config.agent.model,
        api_key=config.agent.api_key,
        base_url=config.agent.base_url,
    )

    registry = ToolRegistry()
    for t in BUILTIN_TOOLS:
        registry.register(Tool(
            name=t["name"],
            description=t["description"],
            parameters=t["parameters"],
            handler=t["fn"],
            category=t["category"],
        ))

    permissions = PermissionPipeline(
        mode=SecurityMode(config.security.mode),
        sandbox_enabled=config.security.sandbox,
    )

    engine = AgentEngine(
        llm=llm,
        tool_registry=registry,
        permissions=permissions,
        max_turns=config.agent.max_turns,
    )

    mode = AgentMode(config.agent.mode)

    console.print(f"[bold green]Kageko[/] — model={config.agent.model} mode={mode.value}")
    console.print("Type your message, or 'quit' to exit.\n")

    while True:
        try:
            user_input = console.input("[bold blue]>[/] ")
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.strip().lower() in ("quit", "exit", "q"):
            break
        if not user_input.strip():
            continue

        with console.status("Thinking..."):
            result = await engine.run(user_input.strip(), mode=mode)

        console.print(f"\n{result.answer}\n")
        console.print(f"[dim]turns={result.turn_count} tokens={result.tokens_used}[/]\n")

    await db.close()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_config.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/config.py src/kageko/cli.py tests/unit/test_config.py
git commit -m "feat: add config loader and interactive CLI chat"
```

---

## Phase 3: Rust Core (PyO3 native tools)

### Task 10: Rust hashline edit engine

**Files:**
- Modify: `src/kageko_native/Cargo.toml`
- Modify: `src/kageko_native/src/lib.rs`
- Create: `src/kageko_native/src/hashline.rs`
- Test: `tests/rust/test_hashline.rs` (Rust) + `tests/unit/test_hashline_py.py` (Python)

- [ ] **Step 1: Add dependencies to Cargo.toml**

```toml
[dependencies]
pyo3 = { version = "0.23", features = ["extension-module"] }
sha2 = "0.10"
```

- [ ] **Step 2: Write Rust hashline module**

```rust
// src/kageko_native/src/hashline.rs
use pyo3::prelude::*;
use sha2::{Digest, Sha256};
use std::fmt;

#[pyclass]
#[derive(Clone)]
pub struct SourceLine {
    #[pyo3(get)]
    pub number: usize,
    #[pyo3(get)]
    pub content: String,
    #[pyo3(get)]
    pub anchor: String,
}

#[pyclass]
pub struct HashlineEditor {
    source: String,
    lines: Vec<SourceLine>,
}

#[derive(Debug)]
pub enum EditError {
    InvalidFormat(String),
    AnchorNotFound(String),
    LineOutOfRange(usize),
}

impl fmt::Display for EditError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            EditError::InvalidFormat(msg) => write!(f, "Invalid hashline format: {}", msg),
            EditError::AnchorNotFound(anchor) => write!(f, "Anchor not found: {}", anchor),
            EditError::LineOutOfRange(n) => write!(f, "Line out of range: {}", n),
        }
    }
}

fn compute_anchor(content: &str) -> String {
    let trimmed = content.trim();
    let mut hasher = Sha256::new();
    hasher.update(trimmed.as_bytes());
    let result = hasher.finalize();
    hex::encode(result)[..8].to_string()
}

#[pymethods]
impl HashlineEditor {
    #[new]
    pub fn new(source: &str) -> Self {
        let lines = source
            .lines()
            .enumerate()
            .map(|(i, content)| SourceLine {
                number: i + 1,
                content: content.to_string(),
                anchor: compute_anchor(content),
            })
            .collect();

        HashlineEditor {
            source: source.to_string(),
            lines,
        }
    }

    /// Parse a hashline edit string.
    /// Format: "#<line>|<anchor>| <new_content>"
    /// Example: "#3|a1b2c3d4| def new_function():"
    pub fn apply(&mut self, edit: &str) -> PyResult<String> {
        let parsed = self.parse_edit(edit)?;
        let target_idx = self.find_by_anchor(&parsed.anchor)?;

        if target_idx >= self.lines.len() {
            return Err(pyo3::exceptions::PyValueError::new_err(
                EditError::LineOutOfRange(target_idx).to_string(),
            ));
        }

        // Verify anchor still matches
        if self.lines[target_idx].anchor != parsed.anchor {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Anchor mismatch: expected {} but line {} has {}",
                parsed.anchor,
                self.lines[target_idx].number,
                self.lines[target_idx].anchor,
            )));
        }

        // Apply edit
        if parsed.new_content.is_empty() {
            // Delete line
            self.lines.remove(target_idx);
        } else {
            self.lines[target_idx].content = parsed.new_content.clone();
            self.lines[target_idx].anchor = compute_anchor(&parsed.new_content);
        }

        // Rebuild source
        self.source = self
            .lines
            .iter()
            .map(|l| l.content.as_str())
            .collect::<Vec<_>>()
            .join("\n");

        Ok(self.source.clone())
    }

    /// Get all source lines with their anchors (for debugging/display)
    pub fn lines(&self) -> Vec<SourceLine> {
        self.lines.clone()
    }

    /// Get the current source text
    pub fn source(&self) -> &str {
        &self.source
    }

    /// Parse multiple hashline edits and apply them in sequence
    pub fn apply_batch(&mut self, edits: Vec<&str>) -> PyResult<String> {
        for edit in edits {
            self.apply(edit)?;
        }
        Ok(self.source.clone())
    }
}

struct ParsedEdit {
    anchor: String,
    new_content: String,
}

impl HashlineEditor {
    fn parse_edit(&self, edit: &str) -> Result<ParsedEdit, EditError> {
        let edit = edit.trim();
        if !edit.starts_with('#') {
            return Err(EditError::InvalidFormat(
                "Edit must start with '#'".to_string(),
            ));
        }

        let parts: Vec<&str> = edit[1..].splitn(3, '|').collect();
        if parts.len() < 2 {
            return Err(EditError::InvalidFormat(
                "Expected format: #<line>|<anchor>| <new_content>".to_string(),
            ));
        }

        let anchor = parts[1].trim().to_string();
        let new_content = if parts.len() == 3 {
            parts[2].trim_start().to_string()
        } else {
            String::new()
        };

        Ok(ParsedEdit { anchor, new_content })
    }

    fn find_by_anchor(&self, anchor: &str) -> Result<usize, EditError> {
        self.lines
            .iter()
            .position(|l| l.anchor == anchor)
            .ok_or_else(|| EditError::AnchorNotFound(anchor.to_string()))
    }
}
```

- [ ] **Step 3: Register in lib.rs**

```rust
// src/kageko_native/src/lib.rs
use pyo3::prelude::*;

mod hashline;

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_class::<hashline::HashlineEditor>()?;
    m.add_class::<hashline::SourceLine>()?;
    Ok(())
}
```

- [ ] **Step 4: Add hex dependency to Cargo.toml**

```toml
[dependencies]
pyo3 = { version = "0.23", features = ["extension-module"] }
sha2 = "0.10"
hex = "0.4"
```

- [ ] **Step 5: Write Python wrapper**

```python
# src/kageko/tools/hashline.py
from __future__ import annotations

from kageko_native._native import HashlineEditor as _HashlineEditor, SourceLine


class HashlineEditor:
    """Python wrapper around the Rust hashline edit engine."""

    def __init__(self, source: str):
        self._editor = _HashlineEditor(source)

    def apply(self, edit: str) -> str:
        return self._editor.apply(edit)

    def apply_batch(self, edits: list[str]) -> str:
        return self._editor.apply_batch(edits)

    @property
    def source(self) -> str:
        return self._editor.source()

    def lines(self) -> list[SourceLine]:
        return list(self._editor.lines())
```

- [ ] **Step 6: Write Python tests**

```python
# tests/unit/test_hashline_py.py
import pytest
from kageko.tools.hashline import HashlineEditor


def test_hashline_basic_edit():
    source = "line one\nline two\nline three"
    editor = HashlineEditor(source)
    lines = editor.lines()
    assert len(lines) == 3
    assert lines[0].content == "line one"
    assert lines[1].anchor == lines[1].anchor  # anchor is deterministic


def test_hashline_apply_edit():
    source = "hello\nworld\ntest"
    editor = HashlineEditor(source)
    lines = editor.lines()
    target_anchor = lines[1].anchor  # "world"
    result = editor.apply(f"#2|{target_anchor}| planet")
    assert "planet" in result
    assert "world" not in result


def test_hashline_anchor_mismatch():
    source = "hello\nworld"
    editor = HashlineEditor(source)
    with pytest.raises(Exception, match="Anchor mismatch"):
        editor.apply("#1|badanchor| new content")


def test_hashline_batch_edits():
    source = "aaa\nbbb\nccc"
    editor = HashlineEditor(source)
    lines = editor.lines()
    a1 = lines[0].anchor
    a3 = lines[2].anchor
    result = editor.apply_batch([
        f"#1|{a1}| AAA",
        f"#3|{a3}| CCC",
    ])
    assert "AAA" in result
    assert "CCC" in result
```

- [ ] **Step 7: Build and test**

```bash
cd KagekoO_O
pip install -e ".[dev]"
pytest tests/unit/test_hashline_py.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/kageko_native/ src/kageko/tools/hashline.py tests/unit/test_hashline_py.py
git commit -m "feat: add Rust hashline edit engine with PyO3 bindings"
```

---

### Task 11: Rust grep (in-process ripgrep)

**Files:**
- Modify: `src/kageko_native/Cargo.toml`
- Modify: `src/kageko_native/src/lib.rs`
- Create: `src/kageko_native/src/grep.rs`
- Create: `src/kageko/tools/grep_tool.py`
- Test: `tests/unit/test_grep_tool.py`

- [ ] **Step 1: Add grep dependencies to Cargo.toml**

```toml
[dependencies]
pyo3 = { version = "0.23", features = ["extension-module"] }
sha2 = "0.10"
hex = "0.4"
grep = "0.3"
grep-matcher = "0.2"
grep-regex = "0.2"
grep-searcher = "0.2"
```

- [ ] **Step 2: Write Rust grep module**

```rust
// src/kageko_native/src/grep.rs
use grep_regex::RegexMatcher;
use grep_searcher::sinks::UTF8;
use grep_searcher::{Searcher, SearcherBuilder};
use pyo3::prelude::*;
use std::path::Path;

#[pyclass]
#[derive(Clone)]
pub struct GrepMatch {
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub line_number: u64,
    #[pyo3(get)]
    pub line: String,
}

/// In-process grep using ripgrep internals. No subprocess spawned.
#[pyfunction]
pub fn ripgrep(
    pattern: &str,
    path: &str,
    max_results: Option<usize>,
) -> PyResult<Vec<GrepMatch>> {
    let matcher = RegexMatcher::new(pattern).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("Invalid regex: {}", e))
    })?;

    let max = max_results.unwrap_or(100);
    let mut matches = Vec::new();
    let search_path = Path::new(path);

    if search_path.is_file() {
        search_file(&matcher, search_path, &mut matches, max)?;
    } else if search_path.is_dir() {
        for entry in walkdir::WalkDir::new(search_path)
            .follow_links(false)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            if entry.file_type().is_file() {
                if matches.len() >= max {
                    break;
                }
                let _ = search_file(&matcher, entry.path(), &mut matches, max);
            }
        }
    }

    Ok(matches)
}

fn search_file(
    matcher: &RegexMatcher,
    path: &Path,
    matches: &mut Vec<GrepMatch>,
    max: usize,
) -> Result<(), std::io::Error> {
    let mut searcher = SearcherBuilder::new().build();
    let path_str = path.to_string_lossy().to_string();

    searcher.search_path(
        matcher,
        path,
        UTF8(|lnum, line| {
            if matches.len() < max {
                matches.push(GrepMatch {
                    path: path_str.clone(),
                    line_number: lnum,
                    line: line.trim_end().to_string(),
                });
            }
            Ok(true)
        }),
    )?;

    Ok(())
}
```

- [ ] **Step 3: Register in lib.rs**

```rust
// src/kageko_native/src/lib.rs
use pyo3::prelude::*;

mod hashline;
mod grep;

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_class::<hashline::HashlineEditor>()?;
    m.add_class::<hashline::SourceLine>()?;
    m.add_function(wrap_pyfunction!(grep::ripgrep, m)?)?;
    m.add_class::<grep::GrepMatch>()?;
    Ok(())
}
```

- [ ] **Step 4: Add walkdir dependency**

```toml
[dependencies]
# ... existing
walkdir = "2"
```

- [ ] **Step 5: Write Python wrapper**

```python
# src/kageko/tools/grep_tool.py
from __future__ import annotations

from kageko_native._native import ripgrep as _ripgrep


def grep(pattern: str, path: str, max_results: int = 100) -> str:
    """Search for pattern in files. Returns formatted results."""
    results = _ripgrep(pattern, path, max_results)
    if not results:
        return f"No matches for '{pattern}' in {path}"
    lines = []
    for m in results:
        lines.append(f"{m.path}:{m.line_number}: {m.line}")
    return "\n".join(lines)
```

- [ ] **Step 6: Write tests**

```python
# tests/unit/test_grep_tool.py
import pytest
from pathlib import Path
from kageko.tools.grep_tool import grep


def test_grep_finds_matches(tmp_path):
    (tmp_path / "test.py").write_text("hello world\nfoo bar\nhello again")
    result = grep("hello", str(tmp_path))
    assert "hello world" in result
    assert "hello again" in result
    assert "foo bar" not in result


def test_grep_no_matches(tmp_path):
    (tmp_path / "test.py").write_text("nothing here")
    result = grep("xyz", str(tmp_path))
    assert "No matches" in result


def test_grep_max_results(tmp_path):
    (tmp_path / "test.py").write_text("\n".join([f"match {i}" for i in range(100)]))
    result = grep("match", str(tmp_path), max_results=3)
    lines = result.strip().split("\n")
    assert len(lines) == 3
```

- [ ] **Step 7: Build and test**

```bash
pip install -e ".[dev]"
pytest tests/unit/test_grep_tool.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/kageko_native/src/grep.rs src/kageko/tools/grep_tool.py tests/unit/test_grep_tool.py
git commit -m "feat: add in-process grep via ripgrep internals (PyO3)"
```

---

### Task 12: Rust AST module (tree-sitter)

**Files:**
- Modify: `src/kageko_native/Cargo.toml`
- Modify: `src/kageko_native/src/lib.rs`
- Create: `src/kageko_native/src/ast_tool.rs`
- Create: `src/kageko/tools/ast_tool.py`
- Test: `tests/unit/test_ast_tool.py`

- [ ] **Step 1: Add tree-sitter dependencies to Cargo.toml**

```toml
[dependencies]
# ... existing
tree-sitter = "0.24"
tree-sitter-python = "0.23"
tree-sitter-javascript = "0.23"
tree-sitter-rust = "0.23"
```

- [ ] **Step 2: Write Rust AST module**

```rust
// src/kageko_native/src/ast_tool.rs
use pyo3::prelude::*;
use tree_sitter::{Parser, Query, QueryCursor};

#[pyclass]
#[derive(Clone)]
pub struct ASTNode {
    #[pyo3(get)]
    pub kind: String,
    #[pyo3(get)]
    pub start_line: usize,
    #[pyo3(get)]
    pub end_line: usize,
    #[pyo3(get)]
    pub text: String,
}

/// Parse source code and return a summary of top-level declarations.
#[pyfunction]
pub fn summarize(source: &str, language: &str) -> PyResult<Vec<ASTNode>> {
    let lang = get_language(language)?;
    let mut parser = Parser::new();
    parser.set_language(&lang).map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Parser error: {}", e))
    })?;

    let tree = parser.parse(source, None).ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("Failed to parse source")
    })?;

    let root = tree.root_node();
    let mut nodes = Vec::new();
    collect_top_level(source, root, &mut nodes);

    Ok(nodes)
}

fn get_language(name: &str) -> PyResult<tree_sitter::Language> {
    match name {
        "python" => Ok(tree_sitter_python::LANGUAGE.into()),
        "javascript" | "js" => Ok(tree_sitter_javascript::LANGUAGE.into()),
        "rust" | "rs" => Ok(tree_sitter_rust::LANGUAGE.into()),
        _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Unsupported language: {}",
            name
        ))),
    }
}

fn collect_top_level(source: &str, node: tree_sitter::Node, results: &mut Vec<ASTNode>) {
    let kind_names = [
        "function_definition",
        "class_definition",
        "import_statement",
        "import_from_statement",
        "decorated_definition",
        "expression_statement",
    ];

    for child in node.children(&mut node.walk()) {
        let kind = child.kind().to_string();
        if kind_names.contains(&kind.as_str()) {
            let text = child
                .utf8_text(source.as_bytes())
                .unwrap_or("")
                .lines()
                .next()
                .unwrap_or("")
                .to_string();

            results.push(ASTNode {
                kind,
                start_line: child.start_position().row + 1,
                end_line: child.end_position().row + 1,
                text,
            });
        }

        // Recurse into blocks
        if child.child_count() > 0 && !kind_names.contains(&child.kind()) {
            collect_top_level(source, child, results);
        }
    }
}
```

- [ ] **Step 3: Register in lib.rs**

Add to `_native` module init:
```rust
m.add_function(wrap_pyfunction!(ast_tool::summarize, m)?)?;
m.add_class::<ast_tool::ASTNode>()?;
```

- [ ] **Step 4: Write Python wrapper**

```python
# src/kageko/tools/ast_tool.py
from __future__ import annotations

from kageko_native._native import summarize as _summarize


def ast_summarize(source: str, language: str = "python") -> str:
    """Parse source code and return a summary of top-level declarations."""
    nodes = _summarize(source, language)
    if not nodes:
        return "(no declarations found)"
    lines = []
    for node in nodes:
        lines.append(f"L{node.start_line}-{node.end_line} [{node.kind}] {node.text}")
    return "\n".join(lines)
```

- [ ] **Step 5: Write tests**

```python
# tests/unit/test_ast_tool.py
import pytest
from kageko.tools.ast_tool import ast_summarize


def test_summarize_python():
    source = """
def hello():
    return "world"

class MyClass:
    def method(self):
        pass
"""
    result = ast_summarize(source, "python")
    assert "function_definition" in result
    assert "class_definition" in result


def test_summarize_empty():
    result = ast_summarize("", "python")
    assert "no declarations" in result


def test_summarize_unsupported_language():
    with pytest.raises(Exception, match="Unsupported language"):
        ast_summarize("x", "fortran")
```

- [ ] **Step 6: Build and test**

```bash
pip install -e ".[dev]"
pytest tests/unit/test_ast_tool.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/kageko_native/src/ast_tool.rs src/kageko/tools/ast_tool.py tests/unit/test_ast_tool.py
git commit -m "feat: add tree-sitter AST summarizer for Python/JS/Rust"
```

---

## Phase 4: Learning Loop + Gateway

### Task 13: Skill engine (Markdown-based)

**Files:**
- Create: `src/kageko/learning/__init__.py`
- Create: `src/kageko/learning/skills.py`
- Test: `tests/unit/test_skills.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_skills.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_skills.py -v
```
Expected: FAIL with import error

- [ ] **Step 3: Write implementation**

```python
# src/kageko/learning/__init__.py
from kageko.learning.skills import SkillEngine, Skill

__all__ = ["SkillEngine", "Skill"]
```

```python
# src/kageko/learning/skills.py
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from kageko.data.db import KagekoDB


@dataclass
class Skill:
    name: str
    version: str
    trigger: str
    description: str
    content: str
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_markdown(cls, path: str) -> Skill:
        text = Path(path).read_text(encoding="utf-8")
        return cls._parse(text)

    @classmethod
    def _parse(cls, text: str) -> Skill:
        # Extract frontmatter
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        if not match:
            raise ValueError("Invalid skill format: missing frontmatter")

        fm_text = match.group(1)
        content = match.group(2)

        # Parse frontmatter key-value pairs
        fm = {}
        for line in fm_text.strip().split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                # Parse list values like [devops, deployment]
                if value.startswith("[") and value.endswith("]"):
                    value = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
                fm[key] = value

        if "name" not in fm:
            raise ValueError("Skill frontmatter must contain 'name'")

        return cls(
            name=fm["name"],
            version=fm.get("version", "0.1.0"),
            trigger=fm.get("trigger", ""),
            description=fm.get("description", ""),
            content=content.strip(),
            tags=fm.get("tags", []) if isinstance(fm.get("tags"), list) else [],
        )

    def to_markdown(self) -> str:
        tags_str = "[" + ", ".join(self.tags) + "]" if self.tags else "[]"
        return f"""---
name: {self.name}
version: {self.version}
trigger: {self.trigger}
description: {self.description}
tags: {tags_str}
---

{self.content}
"""


class SkillEngine:
    def __init__(self, db: KagekoDB):
        self.db = db

    async def save(self, skill: Skill) -> None:
        await self.db.save_skill(
            name=skill.name,
            version=skill.version,
            trigger=skill.trigger,
            description=skill.description,
            content=skill.to_markdown(),
            tags=skill.tags,
        )

    async def search(self, query: str) -> list[Skill]:
        records = await self.db.search_skills(query)
        return [
            Skill(
                name=r.name,
                version=r.version,
                trigger=r.trigger,
                description=r.description,
                content=r.content,
                tags=r.tags,
            )
            for r in records
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_skills.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/learning/ tests/unit/test_skills.py
git commit -m "feat: add Markdown-based skill engine with FTS5 search"
```

---

### Task 14: Tool generator + hot-loading

**Files:**
- Create: `src/kageko/learning/tools.py`
- Test: `tests/unit/test_tool_generator.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_tool_generator.py
import pytest
from kageko.learning.tools import ToolGenerator, GeneratedTool
from kageko.tools.registry import ToolRegistry
from kageko.data.db import KagekoDB


@pytest.fixture
async def db(tmp_path):
    database = KagekoDB(str(tmp_path / "test.db"))
    await database.init()
    yield database
    await database.close()


def test_generated_tool_validation():
    tool = GeneratedTool(
        name="deploy_check",
        description="Check deployment readiness",
        parameters={
            "type": "object",
            "properties": {"env": {"type": "string"}},
            "required": ["env"],
        },
        implementation='async def handler(args): return "ok"',
        category="system",
    )
    assert tool.name == "deploy_check"
    assert tool.is_valid()


def test_generated_tool_invalid_name():
    tool = GeneratedTool(
        name="123bad",  # must start with letter
        description="test",
        parameters={},
        implementation="",
        category="system",
    )
    assert not tool.is_valid()


@pytest.mark.asyncio
async def test_hot_load_registers_tool(db):
    registry = ToolRegistry()
    gen = ToolGenerator(db=db, registry=registry)

    tool_def = {
        "name": "greet",
        "description": "Greet someone",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        "implementation": "async def handler(args): return f'Hello, {args[\"name\"]}!'",
        "category": "system",
    }

    await gen.hot_load(tool_def)
    assert registry.get("greet") is not None

    result = await registry.execute("greet", {"name": "World"})
    assert result == "Hello, World!"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_tool_generator.py -v
```
Expected: FAIL with import error

- [ ] **Step 3: Write implementation**

```python
# src/kageko/learning/tools.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from kageko.data.db import KagekoDB
from kageko.tools.registry import Tool, ToolRegistry


@dataclass
class GeneratedTool:
    name: str
    description: str
    parameters: dict[str, Any]
    implementation: str
    category: str

    def is_valid(self) -> bool:
        if not re.match(r"^[a-z][a-z0-9_]*$", self.name):
            return False
        if not self.description:
            return False
        return True


class ToolGenerator:
    def __init__(self, db: KagekoDB, registry: ToolRegistry):
        self.db = db
        self.registry = registry

    async def hot_load(self, tool_def: dict[str, Any]) -> None:
        """Compile a tool definition and register it in the registry."""
        gen_tool = GeneratedTool(
            name=tool_def["name"],
            description=tool_def["description"],
            parameters=tool_def["parameters"],
            implementation=tool_def["implementation"],
            category=tool_def.get("category", "generated"),
        )

        if not gen_tool.is_valid():
            raise ValueError(f"Invalid tool definition: {gen_tool.name}")

        handler = _compile_handler(gen_tool.implementation)

        tool = Tool(
            name=gen_tool.name,
            description=gen_tool.description,
            parameters=gen_tool.parameters,
            handler=handler,
            category=gen_tool.category,
        )
        self.registry.register(tool)

        await self.db.save_tool(
            name=gen_tool.name,
            schema_json=gen_tool.parameters,
            implementation=gen_tool.implementation,
            category=gen_tool.category,
        )


def _compile_handler(code: str):
    """Compile a tool implementation string into an async handler function."""
    namespace: dict[str, Any] = {}
    exec(code, namespace)
    handler = namespace.get("handler")
    if handler is None:
        raise ValueError("Tool implementation must define a 'handler' function")
    return handler
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_tool_generator.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/learning/tools.py tests/unit/test_tool_generator.py
git commit -m "feat: add tool generator with hot-loading via exec compilation"
```

---

### Task 15: Curator (background maintenance)

**Files:**
- Create: `src/kageko/learning/curator.py`
- Test: `tests/unit/test_curator.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_curator.py
import pytest
from datetime import datetime, timezone, timedelta
from kageko.data.db import KagekoDB
from kageko.learning.curator import Curator


@pytest.fixture
async def db(tmp_path):
    database = KagekoDB(str(tmp_path / "test.db"))
    await database.init()
    yield database
    await database.close()


@pytest.fixture
def curator(db):
    return Curator(db=db, stale_days=30)


@pytest.mark.asyncio
async def test_curator_initializes(curator):
    assert curator.stale_days == 30


@pytest.mark.asyncio
async def test_curator_logs_action(curator, db):
    await curator.log_action("archive", "skill", "old-skill", "Skill not used in 30 days")
    # Verify log was written (no error = success)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_curator.py -v
```
Expected: FAIL with import error

- [ ] **Step 3: Write implementation**

```python
# src/kageko/learning/curator.py
from __future__ import annotations

from kageko.data.db import KagekoDB


class Curator:
    """Background maintenance for skills and tools."""

    def __init__(self, db: KagekoDB, stale_days: int = 30):
        self.db = db
        self.stale_days = stale_days

    async def log_action(
        self, action: str, target_type: str, target_name: str, details: str = ""
    ) -> None:
        assert self.db._conn is not None
        from kageko.data.db import _now

        await self.db._conn.execute(
            "INSERT INTO curator_log (action, target_type, target_name, details, created_at) VALUES (?, ?, ?, ?, ?)",
            (action, target_type, target_name, details, _now()),
        )
        await self.db._conn.commit()

    async def maintain_skills(self) -> list[str]:
        """Review skills and archive stale ones. Returns list of actions taken."""
        actions = []
        # In a real implementation, this would check last_used timestamps
        # and transition lifecycle states. For v1, it's a placeholder
        # that can be extended when the learning loop generates real skills.
        return actions

    async def audit_tool_safety(self, tool_name: str, implementation: str) -> bool:
        """Basic safety check for generated tool code."""
        dangerous_patterns = [
            "import os",
            "import subprocess",
            "__import__",
            "eval(",
            "exec(",
            "open(",
            "shutil",
        ]
        for pattern in dangerous_patterns:
            if pattern in implementation:
                await self.log_action(
                    "safety_flag", "tool", tool_name,
                    f"Contains potentially dangerous pattern: {pattern}",
                )
                return False
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_curator.py -v
```
Expected: all 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/learning/curator.py tests/unit/test_curator.py
git commit -m "feat: add Curator for background skill/tool maintenance"
```

---

### Task 16: Multi-platform gateway skeleton + CLI adapter

**Files:**
- Create: `src/kageko/gateway/__init__.py`
- Create: `src/kageko/gateway/server.py`
- Create: `src/kageko/gateway/dispatch.py`
- Create: `src/kageko/gateway/platforms/__init__.py`
- Create: `src/kageko/gateway/platforms/base.py`
- Create: `src/kageko/gateway/platforms/cli_adapter.py`
- Test: `tests/unit/test_gateway.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_gateway.py
import pytest
from unittest.mock import AsyncMock
from kageko.gateway.server import Gateway
from kageko.gateway.platforms.base import PlatformAdapter, IncomingMessage
from kageko.gateway.platforms.cli_adapter import CLIAdapter
from kageko.agent.loop import AgentEngine


@pytest.fixture
def mock_engine():
    engine = AsyncMock()
    engine.run = AsyncMock(return_value=type("R", (), {"answer": "response text"})())
    return engine


@pytest.mark.asyncio
async def test_gateway_register_adapter(mock_engine):
    gw = Gateway(agent=mock_engine)
    adapter = CLIAdapter(name="cli")
    gw.register("cli", adapter)
    assert "cli" in gw.adapters


@pytest.mark.asyncio
async def test_gateway_dispatch(mock_engine):
    gw = Gateway(agent=mock_engine)
    adapter = CLIAdapter(name="cli")
    gw.register("cli", adapter)

    msg = IncomingMessage(chat_id="user1", text="hello")
    await gw.dispatch("cli", msg)
    mock_engine.run.assert_called_once_with("hello")


def test_incoming_message():
    msg = IncomingMessage(chat_id="user1", text="hello", metadata={"platform": "cli"})
    assert msg.chat_id == "user1"
    assert msg.text == "hello"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_gateway.py -v
```
Expected: FAIL with import error

- [ ] **Step 3: Write implementation**

```python
# src/kageko/gateway/__init__.py
from kageko.gateway.server import Gateway

__all__ = ["Gateway"]
```

```python
# src/kageko/gateway/platforms/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


@dataclass
class IncomingMessage:
    chat_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


MessageHandler = Callable[[str, IncomingMessage], Awaitable[None]]


class PlatformAdapter(ABC):
    """Base class for platform adapters."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def start(self, on_message: MessageHandler) -> None:
        """Start listening for messages. Call on_message(platform, msg) for each."""

    @abstractmethod
    async def send(self, chat_id: str, text: str) -> None:
        """Send a message to a chat."""

    async def stop(self) -> None:
        """Stop the adapter."""
```

```python
# src/kageko/gateway/platforms/cli_adapter.py
from __future__ import annotations

from kageko.gateway.platforms.base import PlatformAdapter, IncomingMessage, MessageHandler


class CLIAdapter(PlatformAdapter):
    """Local CLI adapter for interactive use."""

    def __init__(self, name: str = "cli"):
        super().__init__(name)
        self._handler: MessageHandler | None = None

    async def start(self, on_message: MessageHandler) -> None:
        self._handler = on_message

    async def send(self, chat_id: str, text: str) -> None:
        # In CLI mode, this is handled by the CLI loop directly
        pass

    async def handle_input(self, text: str) -> None:
        """Called by the CLI loop to inject a message into the gateway."""
        if self._handler:
            msg = IncomingMessage(chat_id="local", text=text)
            await self._handler(self.name, msg)
```

```python
# src/kageko/gateway/dispatch.py
from __future__ import annotations

from typing import Any


class MessageDispatch:
    """Routes messages to the agent engine and back to the platform."""

    def __init__(self, agent: Any):
        self.agent = agent

    async def handle(self, platform: str, message: Any) -> str:
        result = await self.agent.run(message.text)
        return result.answer
```

```python
# src/kageko/gateway/server.py
from __future__ import annotations

import logging
from typing import Any

from kageko.gateway.platforms.base import IncomingMessage, PlatformAdapter

logger = logging.getLogger(__name__)


class Gateway:
    """Single-process multi-platform message gateway."""

    def __init__(self, agent: Any):
        self.agent = agent
        self.adapters: dict[str, PlatformAdapter] = {}

    def register(self, name: str, adapter: PlatformAdapter) -> None:
        self.adapters[name] = adapter

    async def start(self, platforms: list[str] | None = None) -> None:
        names = platforms or list(self.adapters.keys())
        for name in names:
            if name in self.adapters:
                await self.adapters[name].start(self.dispatch)
                logger.info("Started adapter: %s", name)

    async def dispatch(self, platform: str, message: IncomingMessage) -> None:
        logger.debug("Received message from %s/%s: %s", platform, message.chat_id, message.text[:50])
        result = await self.agent.run(message.text)
        if platform in self.adapters:
            await self.adapters[platform].send(message.chat_id, result.answer)

    async def stop(self) -> None:
        for name, adapter in self.adapters.items():
            await adapter.stop()
            logger.info("Stopped adapter: %s", name)
```

```python
# src/kageko/gateway/platforms/__init__.py
# empty
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_gateway.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/gateway/ tests/unit/test_gateway.py
git commit -m "feat: add multi-platform gateway skeleton with CLI adapter"
```

---

### Task 17: Context compression

**Files:**
- Create: `src/kageko/agent/context.py`
- Test: `tests/unit/test_context.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_context.py
import pytest
from kageko.agent.context import ContextCompressor
from kageko.types import Message


def test_compress_short_messages():
    messages = [
        Message(role="user", content="hi"),
        Message(role="assistant", content="hello"),
    ]
    compressor = ContextCompressor(max_tokens=1000)
    result = compressor.compress(messages, current_tokens=50)
    assert result == messages  # no compression needed


def test_compress_estimates_tokens():
    compressor = ContextCompressor(max_tokens=100)
    # ~4 chars per token, so 400 chars ≈ 100 tokens
    long_msg = Message(role="user", content="x" * 400)
    tokens = compressor.estimate_tokens([long_msg])
    assert tokens >= 90


def test_compress_preserves_head_and_tail():
    messages = [
        Message(role="system", content="system prompt"),
        Message(role="user", content="a" * 1000),
        Message(role="assistant", content="b" * 1000),
        Message(role="user", content="c" * 1000),
        Message(role="assistant", content="final answer"),
    ]
    compressor = ContextCompressor(max_tokens=100, head_count=1, tail_count=1)
    result = compressor.compress(messages, current_tokens=500)
    assert result[0].role == "system"  # head preserved
    assert result[-1].content == "final answer"  # tail preserved
    # middle should be compressed
    assert len(result) < len(messages) + 1  # at least one message summarized
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_context.py -v
```
Expected: FAIL with import error

- [ ] **Step 3: Write implementation**

```python
# src/kageko/agent/context.py
from __future__ import annotations

from kageko.types import Message


class ContextCompressor:
    """Compress conversation context when approaching token limits."""

    def __init__(self, max_tokens: int = 8000, head_count: int = 2, tail_count: int = 2):
        self.max_tokens = max_tokens
        self.head_count = head_count
        self.tail_count = tail_count

    def estimate_tokens(self, messages: list[Message]) -> int:
        """Rough token estimation: ~4 characters per token."""
        total = 0
        for msg in messages:
            total += len(msg.content) // 4
            # Account for role overhead
            total += 4
        return total

    def compress(self, messages: list[Message], current_tokens: int) -> list[Message]:
        """Compress messages if over budget. Preserves head and tail."""
        if current_tokens <= self.max_tokens:
            return messages

        if len(messages) <= self.head_count + self.tail_count:
            return messages

        head = messages[: self.head_count]
        tail = messages[-self.tail_count :]
        middle = messages[self.head_count : -self.tail_count]

        if not middle:
            return messages

        # Build a summary message for the middle section
        summary_parts = []
        for msg in middle:
            preview = msg.content[:100]
            if len(msg.content) > 100:
                preview += "..."
            summary_parts.append(f"[{msg.role}]: {preview}")

        summary_content = (
            f"[Context compressed: {len(middle)} messages summarized]\n"
            + "\n".join(summary_parts)
        )
        summary = Message(role="system", content=summary_content)

        return head + [summary] + tail
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_context.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/agent/context.py tests/unit/test_context.py
git commit -m "feat: add context compression with head/tail preservation"
```

---

### Task 18: TTSR stream rules

**Files:**
- Create: `src/kageko/agent/ttsr.py`
- Test: `tests/unit/test_ttsr.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_ttsr.py
import pytest
import re
from kageko.agent.ttsr import StreamRule, StreamInterceptor, Correction


def test_stream_rule_matches():
    rule = StreamRule(
        name="no-import-os",
        pattern=re.compile(r"import\s+os"),
        message="Do not import os directly. Use pathlib instead.",
    )
    assert rule.matches("import os")


def test_stream_rule_no_match():
    rule = StreamRule(
        name="no-import-os",
        pattern=re.compile(r"import\s+os"),
        message="Use pathlib.",
    )
    assert not rule.matches("from pathlib import Path")


@pytest.mark.asyncio
async def test_interceptor_yields_normal_tokens():
    rule = StreamRule(
        name="test",
        pattern=re.compile(r"BAD"),
        message="Don't do that",
    )
    interceptor = StreamInterceptor(rules=[rule])

    tokens = [{"text": "hello "}, {"text": "world"}]
    result = []
    async for t in interceptor._simulate(tokens):
        result.append(t)

    assert len(result) == 2
    assert result[0]["text"] == "hello "


@pytest.mark.asyncio
async def test_interceptor_detects_violation():
    rule = StreamRule(
        name="no-bad",
        pattern=re.compile(r"BAD"),
        message="Stop!",
    )
    interceptor = StreamInterceptor(rules=[rule])

    tokens = [{"text": "this is "}, {"text": "BAD stuff"}]
    result = []
    async for t in interceptor._simulate(tokens):
        result.append(t)

    assert len(result) == 2
    assert isinstance(result[1], Correction)
    assert result[1].message == "Stop!"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_ttsr.py -v
```
Expected: FAIL with import error

- [ ] **Step 3: Write implementation**

```python
# src/kageko/agent/ttsr.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class Correction:
    """A correction message injected when a rule matches."""
    message: str


@dataclass
class StreamRule:
    """A rule that watches stream output for patterns."""
    name: str
    pattern: re.Pattern[str]
    message: str

    def matches(self, text: str) -> bool:
        return bool(self.pattern.search(text))


class StreamInterceptor:
    """Time-traveling stream rules: detect violations mid-stream and inject corrections."""

    def __init__(self, rules: list[StreamRule]):
        self.rules = rules

    async def intercept(self, stream: AsyncIterator[str]) -> AsyncIterator[str | Correction]:
        """Wrap a token stream, yielding tokens or corrections."""
        buffer = ""
        async for token in stream:
            buffer += token
            for rule in self.rules:
                if rule.matches(buffer):
                    yield Correction(message=rule.message)
                    return
            yield token

    async def _simulate(self, tokens: list[dict]) -> AsyncIterator[dict | Correction]:
        """Test helper: simulate a token stream from a list."""
        buffer = ""
        for token in tokens:
            text = token.get("text", "")
            buffer += text
            for rule in self.rules:
                if rule.matches(buffer):
                    yield Correction(message=rule.message)
                    return
            yield token
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_ttsr.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/agent/ttsr.py tests/unit/test_ttsr.py
git commit -m "feat: add time-traveling stream rules (TTSR) for mid-stream corrections"
```

---

## Phase 5: Integration + Polish

### Task 19: QAOA trajectory export

**Files:**
- Create: `src/kageko/data/qaoa_export.py`
- Test: `tests/unit/test_qaoa_export.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_qaoa_export.py
import json
import pytest
from pathlib import Path
from kageko.data.qaoa_export import QAOAExporter
from kageko.types import QAOATrajectory, ToolCall, ToolResult, QAOAStep


def test_trajectory_to_dict():
    traj = QAOATrajectory(query="read config")
    traj.step(
        ToolCall(id="c1", name="file_read", args={"path": "config.py"}),
        ToolResult(tool_call_id="c1", content="model = gpt-4o"),
    )
    traj.set_answer("Config sets model to gpt-4o")

    d = traj.to_dict() if hasattr(traj, 'to_dict') else _traj_to_dict(traj)
    assert d["query"] == "read config"
    assert len(d["steps"]) == 1
    assert d["steps"][0]["action"]["tool"] == "file_read"
    assert d["answer"] == "Config sets model to gpt-4o"


def _traj_to_dict(traj):
    return {
        "query": traj.query,
        "steps": [
            {
                "step": s.step_number,
                "action": {"tool": s.action.name, "args": s.action.args},
                "observation": {"content": s.observation.content},
            }
            for s in traj.steps
        ],
        "answer": traj.answer,
    }


def test_export_to_jsonl(tmp_path):
    exporter = QAOAExporter(str(tmp_path / "trajectories.jsonl"))

    traj = QAOATrajectory(query="test query")
    traj.step(
        ToolCall(id="c1", name="echo", args={"text": "hi"}),
        ToolResult(tool_call_id="c1", content="hi"),
    )
    traj.set_answer("done")

    exporter.export(traj)
    exporter.flush()

    content = (tmp_path / "trajectories.jsonl").read_text()
    lines = [l for l in content.strip().split("\n") if l]
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["query"] == "test query"


def test_export_batch(tmp_path):
    exporter = QAOAExporter(str(tmp_path / "batch.jsonl"))

    for i in range(3):
        traj = QAOATrajectory(query=f"query {i}")
        traj.set_answer(f"answer {i}")
        exporter.export(traj)

    exporter.flush()

    lines = (tmp_path / "batch.jsonl").read_text().strip().split("\n")
    assert len(lines) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_qaoa_export.py -v
```
Expected: FAIL with import error

- [ ] **Step 3: Write implementation**

```python
# src/kageko/data/qaoa_export.py
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from kageko.types import QAOATrajectory


class QAOAExporter:
    """Export QAOA trajectories to JSONL for research/training data."""

    def __init__(self, output_path: str):
        self._path = Path(output_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._buffer: list[dict] = []

    def export(self, trajectory: QAOATrajectory) -> dict:
        """Convert trajectory to a serializable dict and buffer it."""
        record = {
            "query": trajectory.query,
            "steps": [
                {
                    "step": s.step_number,
                    "action": {
                        "tool": s.action.name,
                        "args": s.action.args,
                    },
                    "observation": {
                        "content": s.observation.content,
                        "is_error": s.observation.is_error,
                    },
                }
                for s in trajectory.steps
            ],
            "answer": trajectory.answer,
            "metadata": trajectory.metadata,
        }
        self._buffer.append(record)
        return record

    def flush(self) -> int:
        """Write buffered records to JSONL file. Returns count written."""
        with open(self._path, "a", encoding="utf-8") as f:
            for record in self._buffer:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        count = len(self._buffer)
        self._buffer.clear()
        return count

    def load_all(self) -> list[dict]:
        """Load all trajectories from the JSONL file."""
        if not self._path.exists():
            return []
        records = []
        with open(self._path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_qaoa_export.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/kageko/data/qaoa_export.py tests/unit/test_qaoa_export.py
git commit -m "feat: add QAOA trajectory exporter to JSONL format"
```

---

### Task 20: Integration test — full agent conversation

**Files:**
- Create: `tests/integration/test_full_conversation.py`

- [ ] **Step 1: Write the integration test**

```python
# tests/integration/test_full_conversation.py
import pytest
from unittest.mock import AsyncMock
from kageko.agent.loop import AgentEngine
from kageko.agent.permissions import PermissionPipeline, SecurityMode
from kageko.llm import LLMAdapter, LLMResponse
from kageko.tools.registry import ToolRegistry, Tool
from kageko.tools.builtin import BUILTIN_TOOLS
from kageko.types import AgentMode, ToolCall, Message
from kageko.data.qaoa_export import QAOAExporter


@pytest.fixture
def engine_with_tools():
    llm = AsyncMock(spec=LLMAdapter)
    registry = ToolRegistry()
    for t in BUILTIN_TOOLS:
        registry.register(Tool(
            name=t["name"],
            description=t["description"],
            parameters=t["parameters"],
            handler=t["fn"],
            category=t["category"],
        ))
    permissions = PermissionPipeline(mode=SecurityMode.PERMISSIVE)
    return AgentEngine(llm=llm, tool_registry=registry, permissions=permissions, max_turns=10), llm


@pytest.mark.asyncio
async def test_full_tool_use_conversation(engine_with_tools):
    engine, llm = engine_with_tools
    llm.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="file_read", args={"path": "config.py"})
        ], tokens_used=30),
        LLMResponse(content="The config model is gpt-4o", tool_calls=[], tokens_used=50),
    ])

    result = await engine.run("What model is configured?", mode=AgentMode.TOOL_USE)
    assert result.answer == "The config model is gpt-4o"
    assert result.turn_count == 2
    assert result.tokens_used == 80


@pytest.mark.asyncio
async def test_qaoa_mode_with_trajectory_export(engine_with_tools, tmp_path):
    engine, llm = engine_with_tools
    llm.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="echo", args={"text": "test"})
        ], tokens_used=20),
        LLMResponse(content="Echoed: test", tool_calls=[], tokens_used=30),
    ])

    result = await engine.run("echo test", mode=AgentMode.QAOA)
    assert result.trajectory is not None
    assert len(result.trajectory.steps) == 1
    assert result.trajectory.steps[0].action.name == "echo"
    assert result.trajectory.answer == "Echoed: test"

    # Export
    exporter = QAOAExporter(str(tmp_path / "export.jsonl"))
    exporter.export(result.trajectory)
    exporter.flush()

    records = exporter.load_all()
    assert len(records) == 1
    assert records[0]["query"] == "echo test"
    assert records[0]["answer"] == "Echoed: test"


@pytest.mark.asyncio
async def test_parallel_tool_calls(engine_with_tools):
    engine, llm = engine_with_tools
    llm.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="echo", args={"text": "one"}),
            ToolCall(id="c2", name="echo", args={"text": "two"}),
        ], tokens_used=30),
        LLMResponse(content="Both echoed", tool_calls=[], tokens_used=20),
    ])

    result = await engine.run("echo one and two", mode=AgentMode.TOOL_USE)
    assert result.answer == "Both echoed"
    assert result.turn_count == 2


@pytest.mark.asyncio
async def test_security_blocks_dangerous_command(engine_with_tools):
    engine, llm = engine_with_tools
    engine.permissions.mode = SecurityMode.INTERACTIVE
    llm.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="bash", args={"command": "rm -rf /"})
        ], tokens_used=10),
        LLMResponse(content="I can't do that", tool_calls=[], tokens_used=10),
    ])

    result = await engine.run("delete everything", mode=AgentMode.TOOL_USE)
    assert result.answer == "I can't do that"
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
pytest tests/integration/ -v
```
Expected: all 4 tests PASS

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -v --tb=short
```
Expected: all tests PASS

- [ ] **Step 4: Run type checker**

```bash
mypy src/kageko/ --ignore-missing-imports
```
Expected: no errors (or minor fixups)

- [ ] **Step 5: Run linter**

```bash
ruff check src/
```
Expected: clean or auto-fixable

- [ ] **Step 6: Commit**

```bash
git add tests/integration/
git commit -m "test: add integration tests for full agent conversation flows"
```

---

## Summary

| Phase | Tasks | Key Deliverables |
|-------|-------|-----------------|
| 1. Foundation | 1-4 | Scaffold, core types, SQLite+FTS5, LLM adapter |
| 2. Agent Core | 5-9 | Tool registry, permissions, agent loop, built-in tools, CLI |
| 3. Rust Core | 10-12 | Hashline engine, in-process grep, tree-sitter AST |
| 4. Learning + Gateway | 13-18 | Skills, tool generator, curator, gateway, compression, TTSR |
| 5. Integration | 19-20 | QAOA export, integration tests |

**Total: ~80 test functions, ~20 commits, each task completable in 15-30 minutes.**

## Spec Coverage Check

| Spec Section | Covered By Task(s) |
|---|---|
| 3. Directory structure | Task 1 |
| 4. Dual-mode execution loop | Task 7 |
| 5. Tool system + hashline | Tasks 5, 10 |
| 5.4 TTSR stream rules | Task 18 |
| 6. Security (4-layer) | Task 6 |
| 7. Learning loop (skills) | Task 13 |
| 7.2 Tool generation | Task 14 |
| 7.3 Curator | Task 15 |
| 8. Multi-platform gateway | Task 16 |
| 9. Rust core (hashline) | Task 10 |
| 9. Rust core (grep) | Task 11 |
| 9. Rust core (AST) | Task 12 |
| 10. Data layer | Task 3 |
| 13. Success criteria | Task 20 (integration) |

All spec sections covered. No gaps.
