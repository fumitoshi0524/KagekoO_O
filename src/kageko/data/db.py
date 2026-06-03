"""Async SQLite database layer with FTS5 full-text search."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import random

import asyncio

import aiosqlite


def _now() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _now_with_offset(days: int = 0) -> str:
    """Return UTC timestamp with an optional day offset in ISO format."""
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SessionRecord:
    id: str
    platform: str
    chat_id: str
    created_at: str
    metadata: dict = field(default_factory=dict)
    title: str = ""
    summary: str = ""


@dataclass
class MessageRecord:
    id: int | None
    session_id: str
    role: str
    content: str
    created_at: str
    reasoning_content: str = ""


@dataclass
class SkillRecord:
    id: int | None
    name: str
    version: str
    trigger: str
    description: str
    content: str
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class MemoryRecord:
    id: str
    content: str
    tags: str
    source: str
    session_id: str
    created_at: str


@dataclass
class TrajectoryRecord:
    id: int | None
    query: str
    steps_json: str
    answer: str
    created_at: str


# ---------------------------------------------------------------------------
# FTS5 SQL
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS sessions (
        id          TEXT PRIMARY KEY,
        platform    TEXT NOT NULL,
        chat_id     TEXT NOT NULL,
        created_at  TEXT NOT NULL,
        metadata    TEXT NOT NULL DEFAULT '{}',
        summary            TEXT NOT NULL DEFAULT '',
        title              TEXT NOT NULL DEFAULT '',
        input_tokens       INTEGER DEFAULT 0,
        output_tokens      INTEGER DEFAULT 0,
        cache_read_tokens  INTEGER DEFAULT 0,
        cache_write_tokens INTEGER DEFAULT 0,
        reasoning_tokens   INTEGER DEFAULT 0,
        estimated_cost_usd REAL DEFAULT 0,
        actual_cost_usd    REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS messages (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  TEXT NOT NULL REFERENCES sessions(id),
        role        TEXT NOT NULL,
        content     TEXT NOT NULL,
        reasoning_content TEXT NOT NULL DEFAULT '',
        created_at  TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS skills (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        version     TEXT NOT NULL,
        trigger     TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL DEFAULT '',
        content     TEXT NOT NULL DEFAULT '',
        tags        TEXT NOT NULL DEFAULT '[]',
        state       TEXT NOT NULL DEFAULT 'active',
        last_used   REAL NOT NULL DEFAULT 0,
        pinned      INTEGER NOT NULL DEFAULT 0,
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS tools (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        schema_json TEXT NOT NULL DEFAULT '{}',
        source      TEXT NOT NULL DEFAULT 'manual',
        implementation TEXT NOT NULL DEFAULT '',
        enabled     INTEGER NOT NULL DEFAULT 1,
        created_at  TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS trajectories (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        query       TEXT NOT NULL,
        steps_json  TEXT NOT NULL DEFAULT '[]',
        answer      TEXT NOT NULL DEFAULT '',
        created_at  TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS memory (
        id          TEXT PRIMARY KEY,
        content     TEXT NOT NULL DEFAULT '',
        tags        TEXT NOT NULL DEFAULT '',
        source      TEXT NOT NULL DEFAULT '',
        session_id  TEXT NOT NULL DEFAULT '',
        created_at  TEXT NOT NULL DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS curator_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        action      TEXT NOT NULL,
        detail      TEXT NOT NULL DEFAULT '',
        created_at  TEXT NOT NULL
    );
"""


FTS_SQL = """
-- Unicode61 tokenizer: good for Latin + general text
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    content,
    tags,
    source,
    tokenize='unicode61'
);

-- Trigram tokenizer: CJK and substring search support
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts_trgm USING fts5(
    content,
    tokenize='trigram'
);

-- Auto-sync triggers for memory_fts
CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory BEGIN
    INSERT INTO memory_fts(rowid, content, tags, source)
    VALUES (new.rowid, new.content, new.tags, new.source);
END;

CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory BEGIN
    DELETE FROM memory_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memory BEGIN
    DELETE FROM memory_fts WHERE rowid = old.rowid;
    INSERT INTO memory_fts(rowid, content, tags, source)
    VALUES (new.rowid, new.content, new.tags, new.source);
END;

-- Auto-sync triggers for memory_fts_trgm
CREATE TRIGGER IF NOT EXISTS memory_trgm_ai AFTER INSERT ON memory BEGIN
    INSERT INTO memory_fts_trgm(rowid, content)
    VALUES (new.rowid, new.content);
END;

CREATE TRIGGER IF NOT EXISTS memory_trgm_ad AFTER DELETE ON memory BEGIN
    DELETE FROM memory_fts_trgm WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS memory_trgm_au AFTER UPDATE ON memory BEGIN
    DELETE FROM memory_fts_trgm WHERE rowid = old.rowid;
    INSERT INTO memory_fts_trgm(rowid, content)
    VALUES (new.rowid, new.content);
END;

-- Session FTS (trigram for CJK support in session titles)
CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(
    title,
    summary,
    platform,
    tokenize='trigram'
);

CREATE TRIGGER IF NOT EXISTS sessions_ai AFTER INSERT ON sessions BEGIN
    INSERT INTO sessions_fts(rowid, title, summary, platform)
    VALUES (new.rowid, new.title, new.summary, new.platform);
END;

CREATE TRIGGER IF NOT EXISTS sessions_ad AFTER DELETE ON sessions BEGIN
    DELETE FROM sessions_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS sessions_au AFTER UPDATE ON sessions BEGIN
    DELETE FROM sessions_fts WHERE rowid = old.rowid;
    INSERT INTO sessions_fts(rowid, title, summary, platform)
    VALUES (new.rowid, new.title, new.summary, new.platform);
END;
"""


# ---------------------------------------------------------------------------
# KagekoDB
# ---------------------------------------------------------------------------


class KagekoDB:
    """Async SQLite wrapper with FTS5 virtual tables for skills and memory."""

    def __init__(self, path: str = "kageko.db") -> None:
        from pathlib import Path
        self._path = str(Path(path).expanduser())
        self._db: aiosqlite.Connection | None = None
        self._write_count = 0

    # ---- lifecycle --------------------------------------------------------

    async def init(self) -> None:
        from pathlib import Path
        db_path = Path(self._path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA synchronous=NORMAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        self._write_count = 0
        await self._create_tables()
        await self._migrate_session_title()
        await self._migrate_session_summary()
        await self._rebuild_sessions_fts()
        await self._rebuild_memory_table()
        await self._create_fts_indexes()
        await self._repopulate_fts()
        await self._reconcile_columns()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def write_with_retry(
        self, sql: str, params: tuple = (), max_retries: int = 15
    ) -> None:
        """Execute a write with jitter retry on contention."""
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                await self._conn.execute("BEGIN IMMEDIATE")
                await self._conn.execute(sql, params)
                await self._conn.commit()
                self._write_count += 1
                if self._write_count % 50 == 0:
                    await self._conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
                    self._write_count = 0
                return
            except aiosqlite.OperationalError as exc:
                last_exc = exc
                if "locked" not in str(exc).lower():
                    raise
                try:
                    await self._conn.execute("ROLLBACK")
                except Exception:
                    pass
                await asyncio.sleep(random.uniform(0.02, 0.15))
        raise RuntimeError("Max write retries exceeded") from last_exc

    @property
    def _conn(self) -> aiosqlite.Connection:
        assert self._db is not None, "Database not initialised – call init() first"
        return self._db

    # ---- schema -----------------------------------------------------------

    async def _create_tables(self) -> None:
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.executescript(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
                name, trigger, description, content, tags,
                content='skills',
                content_rowid='id'
            );
            """
        )
        await self._conn.commit()

    async def _migrate_session_title(self) -> None:
        """Add title column to sessions if it doesn't exist."""
        cursor = await self._conn.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "title" not in columns:
            await self._conn.execute("ALTER TABLE sessions ADD COLUMN title TEXT NOT NULL DEFAULT ''")
            await self._conn.commit()

    async def _migrate_session_summary(self) -> None:
        """Add summary column to sessions if it doesn't exist."""
        cursor = await self._conn.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "summary" not in columns:
            await self._conn.execute("ALTER TABLE sessions ADD COLUMN summary TEXT NOT NULL DEFAULT ''")
            await self._conn.commit()

    async def _rebuild_memory_table(self) -> None:
        """Migrate memory table if it has INTEGER id (old schema) instead of TEXT."""
        cursor = await self._conn.execute("PRAGMA table_info(memory)")
        columns = await cursor.fetchall()
        id_col = next((c for c in columns if c[1] == "id"), None)
        if id_col is None:
            return
        # type 1 = INTEGER, type 12 or text-like = TEXT
        if id_col[2].upper() == "INTEGER":
            await self._conn.executescript("""
                ALTER TABLE memory RENAME TO _memory_old;
            """)
            await self._conn.executescript("""
                CREATE TABLE memory (
                    id          TEXT PRIMARY KEY,
                    content     TEXT NOT NULL DEFAULT '',
                    tags        TEXT NOT NULL DEFAULT '',
                    source      TEXT NOT NULL DEFAULT '',
                    session_id  TEXT NOT NULL DEFAULT '',
                    created_at  TEXT NOT NULL DEFAULT ''
                );
            """)
            # Old schema columns: id(INTEGER), key, value, source, created_at
            # New columns (tags, session_id) default to empty string
            await self._conn.execute(
                "INSERT INTO memory (id, content, tags, source, session_id, created_at) "
                "SELECT CAST(id AS TEXT), COALESCE(key, '') || ' ' || COALESCE(value, ''), "
                "'', COALESCE(source, ''), '', "
                "COALESCE(created_at, '') FROM _memory_old"
            )
            await self._conn.executescript("DROP TABLE IF EXISTS _memory_old;")
            # Drop and recreate FTS tables since the backing data migrated
            await self._conn.executescript("""
                DROP TABLE IF EXISTS memory_fts;
                DROP TABLE IF EXISTS memory_fts_trgm;
            """)
            await self._conn.commit()

    async def _rebuild_sessions_fts(self) -> None:
        """Drop and recreate sessions_fts to pick up schema changes (e.g. summary column)."""
        await self._conn.executescript("""
            DROP TRIGGER IF EXISTS sessions_ai;
            DROP TRIGGER IF EXISTS sessions_ad;
            DROP TRIGGER IF EXISTS sessions_au;
            DROP TABLE IF EXISTS sessions_fts;
        """)
        await self._conn.commit()

    async def _create_fts_indexes(self) -> None:
        """Create FTS5 virtual tables and triggers."""
        await self._conn.executescript(FTS_SQL)

    async def _repopulate_fts(self) -> None:
        """Ensure all FTS indexes are fully populated from backing tables.

        This repairs FTS state after an unclean restart or migration where
        FTS virtual tables were recreated but existing rows were not indexed.
        """
        # Repopulate memory_fts (unicode61) — only rows missing from FTS
        await self._conn.execute(
            "INSERT OR IGNORE INTO memory_fts(rowid, content, tags, source) "
            "SELECT m.rowid, m.content, m.tags, m.source FROM memory m"
        )
        # Repopulate memory_fts_trgm — only rows missing from FTS
        await self._conn.execute(
            "INSERT OR IGNORE INTO memory_fts_trgm(rowid, content) "
            "SELECT m.rowid, m.content FROM memory m"
        )
        # Repopulate sessions_fts — only rows missing from FTS
        await self._conn.execute(
            "INSERT OR IGNORE INTO sessions_fts(rowid, title, summary, platform) "
            "SELECT s.rowid, s.title, s.summary, s.platform FROM sessions s"
        )
        await self._conn.commit()

    async def _reconcile_columns(self) -> None:
        """Declarative schema reconciliation.

        Parses SCHEMA_SQL to find declared columns, diffs against live columns,
        and ADDs missing ones. Eliminates migration chains for column additions.
        """
        import re

        table_pattern = re.compile(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\((.*?)\);",
            re.IGNORECASE | re.DOTALL,
        )
        for match in table_pattern.finditer(SCHEMA_SQL):
            table_name = match.group(1)
            columns_block = match.group(2)

            declared_cols = {}
            for line in columns_block.split("\n"):
                line = line.strip().rstrip(",")
                if not line or line.startswith("--"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    col_name = parts[0].strip('"')
                    col_type = parts[1].upper()
                    if col_name.upper() in (
                        "PRIMARY", "UNIQUE", "CHECK", "FOREIGN", "CONSTRAINT",
                    ):
                        continue
                    declared_cols[col_name] = col_type

            cursor = await self._conn.execute(f"PRAGMA table_info({table_name})")
            live_rows = await cursor.fetchall()
            live_cols = {row[1] for row in live_rows}

            for col_name, col_type in declared_cols.items():
                if col_name not in live_cols:
                    await self._conn.execute(
                        f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                    )

        await self._conn.commit()

    # ---- helpers ----------------------------------------------------------

    async def list_tables(self) -> list[str]:
        cursor = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        rows = await cursor.fetchall()
        return [row["name"] for row in rows]

    # ---- sessions ---------------------------------------------------------

    async def create_session(
        self,
        platform: str,
        chat_id: str,
        metadata: dict | None = None,
        title: str = "",
        summary: str = "",
    ) -> SessionRecord:
        sid = uuid.uuid4().hex
        now = _now()
        meta = json.dumps(metadata or {})
        await self._conn.execute(
            "INSERT INTO sessions (id, platform, chat_id, created_at, metadata, title, summary) VALUES (?,?,?,?,?,?,?)",
            (sid, platform, chat_id, now, meta, title, summary),
        )
        await self._conn.commit()
        return SessionRecord(id=sid, platform=platform, chat_id=chat_id, created_at=now, metadata=metadata or {}, title=title, summary=summary)

    async def list_sessions(self, limit: int = 20) -> list[SessionRecord]:
        cursor = await self._conn.execute(
            "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [
            SessionRecord(
                id=r["id"], platform=r["platform"], chat_id=r["chat_id"],
                created_at=r["created_at"], metadata=json.loads(r["metadata"]),
                title=r["title"] if "title" in r.keys() else "",
                summary=r["summary"] if "summary" in r.keys() else "",
            )
            for r in rows
        ]

    async def get_session_by_chat_id(self, platform: str, chat_id: str) -> SessionRecord | None:
        cursor = await self._conn.execute(
            "SELECT * FROM sessions WHERE platform=? AND chat_id=?", (platform, chat_id)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return SessionRecord(
            id=row["id"], platform=row["platform"], chat_id=row["chat_id"],
            created_at=row["created_at"], metadata=json.loads(row["metadata"]),
            title=row["title"] if "title" in row.keys() else "",
            summary=row["summary"] if "summary" in row.keys() else "",
        )

    async def delete_session(self, session_id: str) -> None:
        await self._conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        await self._conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        await self._conn.commit()

    async def delete_messages_by_ids(self, ids: list[int]) -> None:
        """Delete specific messages by their IDs."""
        if not ids:
            return
        placeholders = ",".join("?" * len(ids))
        await self._conn.execute(
            f"DELETE FROM messages WHERE id IN ({placeholders})", ids,
        )
        await self._conn.commit()

    async def set_session_title(self, session_id: str, title: str) -> None:
        await self._conn.execute(
            "UPDATE sessions SET title=? WHERE id=?", (title, session_id)
        )
        await self._conn.commit()

    async def set_session_summary(self, session_id: str, summary: str) -> None:
        await self._conn.execute(
            "UPDATE sessions SET summary=? WHERE id=?", (summary, session_id)
        )
        await self._conn.commit()

    async def update_session_tokens(
        self,
        session_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        reasoning_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
    ) -> None:
        """Increment token counters for a session."""
        await self.write_with_retry(
            "UPDATE sessions SET "
            "input_tokens = input_tokens + ?, "
            "output_tokens = output_tokens + ?, "
            "cache_read_tokens = cache_read_tokens + ?, "
            "cache_write_tokens = cache_write_tokens + ?, "
            "reasoning_tokens = reasoning_tokens + ?, "
            "estimated_cost_usd = estimated_cost_usd + ? "
            "WHERE id = ?",
            (
                input_tokens, output_tokens, cache_read_tokens,
                cache_write_tokens, reasoning_tokens,
                estimated_cost_usd, session_id,
            ),
        )

    async def get_session(self, session_id: str) -> SessionRecord | None:
        cursor = await self._conn.execute(
            "SELECT * FROM sessions WHERE id=?", (session_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return SessionRecord(
            id=row["id"],
            platform=row["platform"],
            chat_id=row["chat_id"],
            created_at=row["created_at"],
            metadata=json.loads(row["metadata"]),
            title=row["title"] if "title" in row.keys() else "",
            summary=row["summary"] if "summary" in row.keys() else "",
        )

    # ---- messages ---------------------------------------------------------

    async def append_message(self, session_id: str, role: str, content: str, reasoning_content: str = "") -> MessageRecord:
        now = _now()
        cursor = await self._conn.execute(
            "INSERT INTO messages (session_id, role, content, reasoning_content, created_at) VALUES (?,?,?,?,?)",
            (session_id, role, content, reasoning_content, now),
        )
        await self._conn.commit()
        return MessageRecord(id=cursor.lastrowid, session_id=session_id, role=role, content=content, created_at=now, reasoning_content=reasoning_content)

    async def get_messages(self, session_id: str) -> list[MessageRecord]:
        cursor = await self._conn.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY id", (session_id,)
        )
        rows = await cursor.fetchall()
        return [
            MessageRecord(
                id=r["id"],
                session_id=r["session_id"],
                role=r["role"],
                content=r["content"],
                created_at=r["created_at"],
                reasoning_content=(r["reasoning_content"] or "") if "reasoning_content" in r.keys() else "",
            )
            for r in rows
        ]

    async def append_messages_batch(self, session_id: str, messages: list[tuple[str, str]]) -> list[MessageRecord]:
        now = _now()
        records: list[MessageRecord] = []
        for role, content in messages:
            cursor = await self._conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
                (session_id, role, content, now),
            )
            records.append(
                MessageRecord(id=cursor.lastrowid, session_id=session_id, role=role, content=content, created_at=now)
            )
        await self._conn.commit()
        return records

    # ---- skills -----------------------------------------------------------

    async def save_skill(
        self,
        name: str,
        version: str,
        trigger: str = "",
        description: str = "",
        content: str = "",
        tags: list[str] | None = None,
    ) -> SkillRecord:
        now = _now()
        tags = tags or []
        tags_json = json.dumps(tags)
        await self._conn.execute(
            """INSERT INTO skills (name, version, trigger, description, content, tags, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(name) DO UPDATE SET
                 version=excluded.version,
                 trigger=excluded.trigger,
                 description=excluded.description,
                 content=excluded.content,
                 tags=excluded.tags,
                 updated_at=excluded.updated_at""",
            (name, version, trigger, description, content, tags_json, now, now),
        )
        # Keep FTS in sync — rebuild the index from the backing table
        await self._conn.execute("INSERT INTO skills_fts(skills_fts) VALUES ('rebuild')")
        await self._conn.commit()
        return SkillRecord(
            id=None, name=name, version=version, trigger=trigger,
            description=description, content=content, tags=tags,
            created_at=now, updated_at=now,
        )

    async def search_skills(self, query: str) -> list[SkillRecord]:
        cursor = await self._conn.execute(
            """SELECT s.* FROM skills s
               JOIN skills_fts f ON s.id = f.rowid
               WHERE skills_fts MATCH ?
               ORDER BY rank""",
            (query,),
        )
        rows = await cursor.fetchall()
        return [
            SkillRecord(
                id=r["id"], name=r["name"], version=r["version"],
                trigger=r["trigger"], description=r["description"],
                content=r["content"], tags=json.loads(r["tags"]),
                created_at=r["created_at"], updated_at=r["updated_at"],
            )
            for r in rows
        ]

    # ---- tools ------------------------------------------------------------

    async def save_tool(
        self,
        name: str,
        description: str = "",
        schema_json: str = "{}",
        enabled: bool = True,
    ) -> None:
        now = _now()
        await self._conn.execute(
            """INSERT INTO tools (name, description, schema_json, enabled, created_at)
               VALUES (?,?,?,?,?)
               ON CONFLICT(name) DO UPDATE SET
                 description=excluded.description,
                 schema_json=excluded.schema_json,
                 enabled=excluded.enabled""",
            (name, description, schema_json, int(enabled), now),
        )
        await self._conn.commit()

    # ---- memory -----------------------------------------------------------

    async def save_memory(self, content: str, tags: str = "", source: str = "", session_id: str = "") -> MemoryRecord:
        now = _now()
        mem_id = uuid.uuid4().hex
        await self._conn.execute(
            "INSERT INTO memory (id, content, tags, source, session_id, created_at) VALUES (?,?,?,?,?,?)",
            (mem_id, content, tags, source, session_id, now),
        )
        await self._conn.commit()
        return MemoryRecord(id=mem_id, content=content, tags=tags, source=source, session_id=session_id, created_at=now)

    async def search_memory(self, query: str, limit: int = 10) -> list[dict]:
        """Search memory using FTS5. Falls back to trigram for CJK."""
        # Try unicode61 first (better relevance for Latin text)
        cursor = await self._conn.execute(
            "SELECT m.id, m.content, m.tags, m.source, m.session_id, m.created_at "
            "FROM memory_fts fts JOIN memory m ON fts.rowid = m.rowid "
            "WHERE memory_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        )
        rows = await cursor.fetchall()
        if rows:
            return [dict(r) for r in rows]
        # Fallback to trigram (better for CJK / substring)
        cursor = await self._conn.execute(
            "SELECT m.id, m.content, m.tags, m.source, m.session_id, m.created_at "
            "FROM memory_fts_trgm fts JOIN memory m ON fts.rowid = m.rowid "
            "WHERE memory_fts_trgm MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ---- trajectories -----------------------------------------------------

    async def save_trajectory(self, data: dict) -> TrajectoryRecord:
        now = _now()
        query = data.get("query", "")
        steps_json = json.dumps(data.get("steps", []))
        answer = data.get("answer", "")
        cursor = await self._conn.execute(
            "INSERT INTO trajectories (query, steps_json, answer, created_at) VALUES (?,?,?,?)",
            (query, steps_json, answer, now),
        )
        await self._conn.commit()
        return TrajectoryRecord(
            id=cursor.lastrowid, query=query,
            steps_json=steps_json, answer=answer, created_at=now,
        )

    async def list_trajectories(self) -> list[TrajectoryRecord]:
        cursor = await self._conn.execute(
            "SELECT * FROM trajectories ORDER BY id"
        )
        rows = await cursor.fetchall()
        return [
            TrajectoryRecord(
                id=r["id"], query=r["query"],
                steps_json=r["steps_json"], answer=r["answer"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    async def log_curator_action(self, action: str, detail: str) -> None:
        """Log a curator maintenance action."""
        now = _now()
        await self._conn.execute(
            "INSERT INTO curator_log (action, detail, created_at) VALUES (?, ?, ?)",
            (action, detail, now),
        )
        await self._conn.commit()

    # ---- recent trajectories (for QAOA tool generation) --------------------

    async def get_recent_trajectories(self, days: int = 30) -> list[dict]:
        """Get trajectories from the last N days, with parsed steps."""
        import time as _time
        cutoff = _now_with_offset(days=-days)
        cursor = await self._conn.execute(
            "SELECT * FROM trajectories WHERE created_at >= ? ORDER BY id DESC",
            (cutoff,),
        )
        rows = await cursor.fetchall()
        result: list[dict] = []
        for r in rows:
            try:
                steps = json.loads(r["steps_json"])
            except (json.JSONDecodeError, KeyError):
                steps = []
            result.append({
                "id": r["id"],
                "query": r["query"],
                "actions": steps,  # expected by ToolGenerator.analyze_and_generate
                "answer": r["answer"],
                "created_at": r["created_at"],
            })
        return result

    async def get_trajectory_count(self) -> int:
        """Return total number of trajectories."""
        cursor = await self._conn.execute("SELECT COUNT(*) FROM trajectories")
        row = await cursor.fetchone()
        return row[0] if row else 0

    # ---- memory listing / stats -------------------------------------------

    async def list_memory(self, limit: int = 20) -> list[MemoryRecord]:
        """List recent memory entries."""
        cursor = await self._conn.execute(
            "SELECT * FROM memory ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [
            MemoryRecord(
                id=r["id"], content=r["content"], tags=r["tags"],
                source=r["source"], session_id=r["session_id"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    async def get_memory_count(self) -> int:
        """Return total number of memory entries."""
        cursor = await self._conn.execute("SELECT COUNT(*) FROM memory")
        row = await cursor.fetchone()
        return row[0] if row else 0

    # ---- skills listing ----------------------------------------------------

    async def get_skills_all(self) -> list[SkillRecord]:
        """List all skills with their state."""
        cursor = await self._conn.execute(
            "SELECT * FROM skills ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            SkillRecord(
                id=r["id"], name=r["name"], version=r["version"],
                trigger=r["trigger"], description=r["description"],
                content=r["content"], tags=json.loads(r["tags"]),
                created_at=r["created_at"], updated_at=r["updated_at"],
            )
            for r in rows
        ]

    async def get_skills_count(self) -> int:
        """Return total number of skills."""
        cursor = await self._conn.execute("SELECT COUNT(*) FROM skills")
        row = await cursor.fetchone()
        return row[0] if row else 0

    # ---- generated tools listing ------------------------------------------

    async def get_tools_generated(self) -> list[dict]:
        """List generated tools."""
        cursor = await self._conn.execute(
            "SELECT name, description, schema_json, source, enabled, created_at "
            "FROM tools WHERE source = 'generated' ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_tools_count(self) -> int:
        """Return total number of tools."""
        cursor = await self._conn.execute("SELECT COUNT(*) FROM tools")
        row = await cursor.fetchone()
        return row[0] if row else 0

    # ---- curator log -------------------------------------------------------

    async def get_curator_log(self, limit: int = 20) -> list[dict]:
        """List recent curator actions."""
        cursor = await self._conn.execute(
            "SELECT * FROM curator_log ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_curator_log_count(self) -> int:
        """Return total number of curator log entries."""
        cursor = await self._conn.execute("SELECT COUNT(*) FROM curator_log")
        row = await cursor.fetchone()
        return row[0] if row else 0

    # ---- skill management (Hermes-style) -----------------------------------

    async def skill_touch(self, name: str) -> None:
        """Bump last_used timestamp for a skill (called when agent invokes it)."""
        import time as _time
        await self._conn.execute(
            "UPDATE skills SET last_used = ? WHERE name = ?",
            (_time.time(), name),
        )
        await self._conn.commit()

    async def skill_pin(self, name: str) -> bool:
        """Pin a skill so it's protected from curator archival. Returns True if found."""
        cursor = await self._conn.execute(
            "UPDATE skills SET pinned = 1 WHERE name = ?", (name,),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def skill_unpin(self, name: str) -> bool:
        """Unpin a skill. Returns True if found."""
        cursor = await self._conn.execute(
            "UPDATE skills SET pinned = 0 WHERE name = ?", (name,),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def skill_patch(self, name: str, find: str, replace: str) -> bool:
        """Fuzzy find-and-replace inside a skill's content. Returns True if found."""
        cursor = await self._conn.execute(
            "SELECT content FROM skills WHERE name = ?", (name,),
        )
        row = await cursor.fetchone()
        if not row:
            return False
        content = row[0]
        if find not in content:
            return False
        new_content = content.replace(find, replace)
        import time as _time
        now = _time.time()
        await self._conn.execute(
            "UPDATE skills SET content = ?, updated_at = datetime(?, 'unixepoch'), last_used = ? WHERE name = ?",
            (new_content, now, now, name),
        )
        await self._conn.commit()
        return True

    async def skill_get_state(self, name: str) -> str | None:
        """Return a skill's state (active/stale/archived) or None."""
        cursor = await self._conn.execute(
            "SELECT state FROM skills WHERE name = ?", (name,),
        )
        row = await cursor.fetchone()
        return row["state"] if row else None

    async def skill_set_state(self, name: str, state: str) -> bool:
        """Explicitly set a skill's state."""
        cursor = await self._conn.execute(
            "UPDATE skills SET state = ? WHERE name = ?", (state, name),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def skill_count_by_state(self) -> dict[str, int]:
        """Return counts per state: {"active": N, "stale": M, "archived": K}."""
        cursor = await self._conn.execute(
            "SELECT state, COUNT(*) as cnt FROM skills GROUP BY state"
        )
        rows = await cursor.fetchall()
        return {r["state"]: r["cnt"] for r in rows}
