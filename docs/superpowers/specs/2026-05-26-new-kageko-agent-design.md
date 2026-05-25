# New Kageko Agent — Design Spec

> Combining strengths from KagekoO_O, hermes-agent, and oh-my-pi into a new agent built from scratch.

## 1. Vision

A three-in-one AI agent that excels at **coding** (hashline editing, LSP/DAP, Rust-native tools), serves as a **general-purpose assistant** (multi-platform gateway, learning loop, skill/tool generation), and supports **research** (QAOA trajectory export, training data generation).

## 2. Tech Stack

- **Python 3.13+**: Agent logic, LLM interaction, permissions, learning, gateway, TUI
- **Rust 2024**: Performance-critical tools (grep, shell, AST, hashline) via PyO3/maturin
- **Runtime**: asyncio + uvloop
- **CLI/TUI**: typer + rich + textual
- **Storage**: SQLite (aiosqlite) + FTS5
- **Build**: `pip install -e .` compiles both Python and Rust via maturin

## 3. Directory Structure

```
KagekoO_O/
├── src/
│   ├── kageko/
│   │   ├── __init__.py
│   │   ├── agent/
│   │   │   ├── loop.py          # Dual-mode agent loop (tool-use / QAOA)
│   │   │   ├── planner.py       # LLM structured planning
│   │   │   ├── context.py       # Context management + compression
│   │   │   ├── permissions.py   # 4-layer permission pipeline
│   │   │   └── ttsr.py          # Time-traveling stream rules
│   │   ├── gateway/
│   │   │   ├── server.py        # aiohttp multi-platform gateway
│   │   │   ├── platforms/       # Per-platform adapters
│   │   │   └── dispatch.py      # Message dispatch
│   │   ├── tools/
│   │   │   ├── registry.py      # Auto-discovery tool registry
│   │   │   ├── builtin/         # Built-in tools (file/bash/browser/...)
│   │   │   ├── generated/       # Auto-generated tools
│   │   │   └── schemas.py       # Tool schema definitions
│   │   ├── learning/
│   │   │   ├── skills.py        # Skill creation/search/execution (Markdown)
│   │   │   ├── tools.py         # Tool generation + hot-loading
│   │   │   ├── curator.py       # Background maintenance for skills + tools
│   │   │   ├── memory.py        # FTS5 cross-session memory
│   │   │   └── models.py        # User modeling
│   │   ├── data/
│   │   │   ├── db.py            # SQLite + FTS5
│   │   │   ├── sessions.py      # Session management
│   │   │   └── qaoa_export.py   # QAOA trajectory export
│   │   ├── tui/                 # Textual TUI
│   │   ├── plugins/             # Plugin system
│   │   ├── cli.py               # CLI entry point
│   │   └── config.py            # Configuration
│   │
│   └── kageko_native/           # Rust extension (PyO3)
│       ├── Cargo.toml
│       └── src/
│           ├── lib.rs           # PyO3 entry
│           ├── shell.rs         # Embedded bash (brush-shell)
│           ├── ast.rs           # tree-sitter 50+ languages
│           ├── hashline.rs      # Anchor-based edit engine
│           └── grep.rs          # In-process ripgrep
│
├── skills/                      # Built-in skill definitions (Markdown)
├── plugins/                     # Built-in plugins
├── tests/
│   ├── unit/
│   ├── integration/
│   └── rust/
├── pyproject.toml               # maturin build bridge
├── Cargo.toml
└── kageko.toml                  # Main config
```

## 4. Agent Core — Dual-Mode Execution Loop

The engine runs the same loop internally. Two modes differ only in observation/record layer.

### 4.1 Standard Tool-Use Mode (daily use)

Compatible with all OpenAI-compatible LLM providers.

```python
class AgentEngine:
    async def _tool_use_loop(self, message: str):
        messages = [UserMessage(message)]
        while True:
            response = await self.llm.chat(messages, tools=self.tool_registry.schemas())
            if response.has_tool_calls():
                results = await self.tool_executor.execute_all(response.tool_calls)
                messages.extend(results)
            else:
                return response.content
```

### 4.2 QAOA Mode (research / training data)

Same loop, wrapped with structured trajectory recording.

```python
    async def _qaoa_loop(self, message: str):
        trajectory = QAOATrajectory(query=message)
        messages = [UserMessage(message)]
        while True:
            response = await self.llm.chat(messages, tools=self.tool_registry.schemas())
            if response.has_tool_calls():
                for call in response.tool_calls:
                    action = Action(tool=call.name, args=call.args)
                    result = await self.tool_executor.execute(call)
                    observation = Observation(content=result)
                    trajectory.step(action, observation)
                messages.extend(self._format_results(response.tool_calls))
            else:
                trajectory.answer(response.content)
                await self.db.save_trajectory(trajectory)
                return AgentResult(answer=response.content, trajectory=trajectory)
```

### 4.3 Key Design Decisions

- **Unified LLM adapter**: Single OpenAI-compatible layer (not 9 separate providers like old KagekoO_O)
- **Parallel tool execution**: Multiple tool_calls in one turn execute concurrently via `asyncio.gather`
- **Structured tool results**: Typed objects, not raw text — enables learning loop and trajectory compression
- **Token-aware context compression**: Auto-triggered when context approaches window limit; protects head/tail, compresses middle

## 5. Tool System + Hashline Editing

### 5.1 Tool Registry

```python
class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._categories: dict[str, list[str]] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool
        self._categories.setdefault(tool.category, []).append(tool.name)

    def schemas(self) -> list[dict]:
        return [t.to_openai_schema() for t in self._tools.values()]
```

### 5.2 Tool Categories

| Category | Tools |
|----------|-------|
| file | read, write, edit, diff |
| shell | bash, eval (Rust in-process) |
| search | grep, ast_grep, web_search |
| code | lsp, debug, hashline_edit |
| browser | navigate, screenshot, click |
| memory | recall, retain, skill_create, session_search |
| system | todo, config, delegate, cron |
| gateway | send_message, list_channels |

### 5.3 Hashline Edit Engine (Rust)

Pioneered by oh-my-pi. The model outputs anchor-based edits instead of line-number-based edits, eliminating string-not-found loops.

```rust
pub struct HashlineEditor {
    source: String,
    lines: Vec<SourceLine>,
}

struct SourceLine {
    number: usize,
    content: String,
    anchor: String,  // first 8 chars of content hash
}

impl HashlineEditor {
    pub fn apply(&mut self, edit: &str) -> Result<String, EditError> {
        let parsed = self.parse_hashline(edit)?;
        let target = self.find_by_anchor(&parsed.anchor)?;
        self.replace_at(target.line_number, &parsed.new_content)
    }
}
```

**Impact** (from oh-my-pi benchmarks):
- Grok Code Fast: 6.7% → 68.3% pass rate
- Grok 4 Fast: output tokens reduced by 61%

### 5.4 Time-Traveling Stream Rules (Python)

```python
class StreamInterceptor:
    def __init__(self, rules: list[StreamRule]):
        self.rules = rules

    async def intercept(self, stream: AsyncIterator[Token]) -> AsyncIterator[Token]:
        buffer = ""
        async for token in stream:
            buffer += token.text
            for rule in self.rules:
                if rule.pattern.search(buffer):
                    yield Correction(rule.message)
                    return
            yield token
```

## 6. Security — 4-Layer Permission Pipeline

Simplified from KagekoO_O's original 7 layers. Removed redundant/unnecessary layers.

```python
class PermissionPipeline:
    async def check(self, tool_call: ToolCall, context: AgentContext) -> Decision:
        # Layer 1: Rule engine — dangerous patterns + user-defined rules
        if decision := self.rule_engine.check(tool_call):
            return decision

        # Layer 2: Sandbox — high-risk tools auto-execute in Docker/container
        if tool_call.name in HIGH_RISK_TOOLS:
            return Decision.EXECUTE_IN_SANDBOX

        # Layer 3: Mode guard — based on current security mode
        if context.mode == Mode.READ_ONLY and tool_call.modifies_state():
            return Decision.DENY

        # Layer 4: Interactive prompt — last resort
        return await self.interactive_prompt(tool_call)
```

## 7. Learning Loop — Skill + Tool Dual Generation

### 7.1 Skills (Markdown format)

```python
class SkillEngine:
    async def create_from_trajectory(self, trajectory: QAOATrajectory):
        raw = await self.llm.extract_skill(trajectory)
        skill = SkillSchema.validate(raw)
        await self.db.save_skill(skill.to_markdown())

    async def search(self, query: str) -> list[Skill]:
        return await self.db.fts_search("skills", query)
```

Skill file format (Markdown):

```markdown
---
name: deploy-check
version: 1.0.0
trigger: When deploying to production
description: Pre-deployment validation checklist
tags: [devops, deployment]
---

# Deploy Check

## Steps
1. Run test suite: `pytest --tb=short`
2. Check for uncommitted changes: `git status --porcelain`
3. Validate config: `python -m kageko.tools validate-config`
4. Check dependencies: `pip check`
```

### 7.2 Tools (JSON Schema format)

```python
class ToolGenerator:
    async def detect_tool_opportunity(self, trajectories: list[QAOATrajectory]):
        pattern = await self.llm.find_repeated_pattern(trajectories)
        if pattern.occurrences >= 3:
            raw = await self.llm.generate_tool(pattern)
            tool = ToolSchema.validate(raw)
            await self.db.save_tool(tool)

    async def hot_load(self, tool_def: dict):
        mod = compile_tool(tool_def["implementation"])
        self.registry.register(Tool(
            name=tool_def["name"],
            schema=tool_def["parameters"],
            handler=mod.execute,
            category=tool_def["category"]
        ))
```

### 7.3 Curator (background maintenance)

```python
class Curator:
    async def maintain(self):
        skills = await self.db.get_active_skills()
        for skill in skills:
            if skill.last_used < self.stale_threshold:
                await self.db.archive_skill(skill.id)

        tools = await self.db.get_generated_tools()
        for tool in tools:
            if not await self.audit_tool_safety(tool):
                await self.db.disable_tool(tool.id)
```

### 7.4 Data Flow

```
Task execution → successful trajectory
    ├── Skill extraction → Markdown validation → save to skills/
    ├── Tool detection (>=3 occurrences) → JSON Schema validation → save to tools/generated/
    │       └── hot_load() → immediately registered to ToolRegistry
    └── QAOA trajectory → saved for research/training data

Curator background:
    ├── Skills: archive stale / merge duplicates / quality assessment
    └── Tools: safety audit / retire low-usage
```

## 8. Multi-Platform Gateway

Single-process gateway with adapter pattern.

```python
class Gateway:
    def __init__(self, agent: AgentEngine):
        self.agent = agent
        self.adapters: dict[str, PlatformAdapter] = {}

    async def start(self, platforms: list[str]):
        for name in platforms:
            adapter = self._load_adapter(name)
            self.adapters[name] = adapter
            await adapter.start(self._on_message)

    async def _on_message(self, platform: str, message: IncomingMessage):
        session = await self.db.get_or_create_session(platform, message.chat_id)
        result = await self.agent.run(message.text, context=session.context)
        await self.adapters[platform].send(message.chat_id, result.answer)
```

### Platform Roadmap

| Phase | Platforms |
|-------|-----------|
| Day-1 | CLI (local) |
| Week-1 | Discord, Feishu |
| Month-1 | Telegram, Slack, WhatsApp, Signal |
| Later | WeChat, DingTalk, Email, Webhook |

## 9. Rust Core Layer (PyO3)

In-process native tools, zero fork/exec overhead.

| Module | Source | Purpose |
|--------|--------|---------|
| `shell` | oh-my-pi `pi-shell` | Embedded bash (brush-shell), persistent sessions |
| `ast` | oh-my-pi `pi-ast` | tree-sitter parsing for 50+ languages, ast-grep |
| `hashline` | oh-my-pi original | Anchor-based edit engine |
| `grep` | ripgrep embedded | In-process full-text search |

Build via maturin: `pip install -e .` compiles both Python and Rust.

## 10. Data Layer (SQLite + FTS5)

| Table | Purpose |
|-------|---------|
| sessions | Session records (FTS5 indexed) |
| skills | Skill definitions (Markdown content + metadata) |
| tools | Auto-generated tools (JSON Schema + implementation) |
| trajectories | QAOA trajectories (research/training data) |
| memory | Cross-session memory entries (FTS5 indexed) |
| curator_log | Curator maintenance log |

## 11. Plugin System (2 Axes)

| Axis | Description | Examples |
|------|-------------|----------|
| Model providers | Any OpenAI-compatible LLM | OpenAI, DeepSeek, Claude, Gemini, Ollama |
| General plugins | Hook-based extensions | Image gen, GitHub integration, browser automation |

Memory providers consolidated into SQLite + FTS5 (not a separate plugin axis).

## 12. Module Origin Map

| New Kageko Module | Origin |
|-------------------|--------|
| Dual-mode execution loop | KagekoO_O QAOA + hermes standard loop |
| Tool registry (auto-discovery) | KagekoO_O 6x8 grid simplified + hermes registry |
| Hashline editing | oh-my-pi original |
| TTSR stream rules | oh-my-pi original |
| Rust coding tools | oh-my-pi (shell/ast/grep) |
| Multi-platform gateway | hermes (30+ platforms → 8-10 core) |
| 4-layer security | KagekoO_O 7 layers simplified |
| Skill auto-generation (MD) | KagekoO_O format + hermes learning loop |
| Tool auto-generation (JSON) | KagekoO_O unique |
| Curator maintenance | hermes curator |
| FTS5 cross-session search | hermes session search |
| Context compression | hermes context_compressor |
| QAOA trajectory export | KagekoO_O data pipeline |
| Plugin system (2-axis) | hermes 3-axis simplified |
| Textual TUI | hermes TUI concept (Python native) |

## 13. Success Criteria

1. Agent can execute coding tasks with hashline editing accuracy matching oh-my-pi benchmarks
2. Agent can serve messages across Discord and Feishu simultaneously
3. Agent can auto-generate skills and tools from repeated successful trajectories
4. Curator maintains skill/tool quality in the background
5. QAOA mode produces exportable training trajectory data
6. Security pipeline blocks dangerous operations without blocking legitimate work
7. Full test suite (unit + integration + Rust) passes

## 14. Out of Scope (Future Iterations)

- Full LSP/DAP integration (after basic coding tools work)
- 30+ platform support (8-10 core platforms first)
- Memory provider plugins (SQLite FTS5 is sufficient for v1)
- Desktop/browser TUI (Textual is sufficient for v1)
- Worktree-isolated subagents (delegation works without isolation first)
