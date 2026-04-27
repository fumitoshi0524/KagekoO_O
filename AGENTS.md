# KagekoO_O — Agent Coding Guide

> This file is written for AI coding agents. Expect the reader to know nothing about the project.

## Project Overview

**KagekoO_O** is a QAOA-oriented agent runtime for building tool-using assistants.
The execution model follows a single canonical loop: **Query -> Action -> Observation -> Answer**.

The project follows the **UniToolCall standard** (arXiv:2604.11557, github.com/EIT-NLP/UniToolCall):
- Tools are classified along 2 dimensions: **6 functional categories** (analysis, operations, system, visualization, search, generate) and **13 application domains** (finance, technology, education, healthcare, entertainment, travel, business, lifestyle, science, social, sports, environment, culture).
- QAOA data generation supports single-hop, multi-hop (2-5 sequential calls), and multi-turn (stateful dialogue with anchor linkage) trajectories.
- Evaluation at function-call, turn, and conversation granularity with strict and flexible metrics.

The project is a **pure Python** codebase (3.13+):
- **Python** provides the core runtime, LLM adapters, tool registry, memory, RAG, data pipelines, and CLI.
- The CLI is built with `typer` + `rich` — no Node.js dependency.

## Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.13+ |
| CLI framework | `typer` + `rich` |
| Python build | `setuptools` (via `pyproject.toml`) |
| Python package manager | `uv` (lockfile present; `.venv` already initialized) |
| LLM providers | OpenAI, DeepSeek, Anthropic (Claude), Google (Gemini) |
| Vector DB | ChromaDB (optional RAG) |
| Session memory | In-memory Python dict (no external DB) |

Key Python dependencies (see `pyproject.toml`):
- `anthropic`, `openai`, `google-genai` — LLM client SDKs
- `chromadb` — vector store for RAG
- `dotenv` — `.env` file loading
- `typer`, `rich` — CLI framework and output formatting

## Repository Layout

```
KagekoO_O/
├── pyproject.toml          # Python project config (setuptools, uv)
├── pyproject.toml          # Python project config (setuptools, uv)
├── uv.lock                 # uv dependency lock (gitignored but tracked)
├── .venv/                  # Pre-initialized uv virtual environment
│
├── qaoa/                   # Main Python package
│   ├── __init__.py         # Public re-exports
│   ├── types.py            # Core dataclasses: QAOATurn, ToolUse, AgentMode, ...
│   ├── engine.py           # QAOAEngine: planning, action execution, skill generation
│   ├── runtime.py          # KagekoRuntime + create_runtime() factory
│   ├── cli.py              # Pure-Python Typer CLI (`kageko` command)
│   ├── learning.py         # Data pipeline: synth, export JSONL, strict evaluation
│   ├── bridge.py           # JSONL stdio bridge (legacy)
│   ├── daemon/             # Persistent JSON-RPC daemon
│   │   ├── server.py       # DaemonServer main loop
│   │   └── protocol.py     # JSON-RPC request dispatch
│   ├── pipeline/           # Tool / skill generation pipeline
│   │   └── core.py         # PipelineCore: LLM-based tool/skill generation
│   └── adapters/
│       ├── __init__.py     # Public adapter re-exports
│       ├── llm.py          # Provider adapters (OpenAI, DeepSeek, Claude, Gemini)
│       ├── tools.py        # ToolRegistry and ToolSpec
│       ├── memory.py       # InMemorySessionStore
│       ├── builtins.py     # Built-in tool pack + skill loader
│       ├── loader.py       # Generated tool auto-loader
│       ├── rag.py          # ChromaDB VectorStore wrapper
│       └── mcp.py          # MCP client scaffolding (placeholder)
│
├── tools/                  # Auto-loaded generated tools
├── skills/                 # Skill definitions
├── KagekoO_O.py            # Compatibility public API (distribution installs)
├── kageko_qaoa.py          # CLI entry point for `kageko-qaoa` command
├── runtime.py              # Compatibility wrapper for runtime imports
└── README.md / README_CN.md
```

## Build and Run Commands

### Python (core runtime)

```bash
# Recommended install (editable)
pip install -e .
# or with uv
uv pip install -e .
```

### Agent CLI (`kageko`)

```bash
# Interactive REPL
kageko --provider openai --api-key $OPENAI_API_KEY

# One-shot chat
kageko --provider openai --api-key $OPENAI_API_KEY chat "Summarize the architecture"

# Tool inspection
kageko --provider openai --api-key $OPENAI_API_KEY tool list
kageko --provider openai --api-key $OPENAI_API_KEY tool show calculator
kageko --provider openai --api-key $OPENAI_API_KEY tool call calculator '{"expression": "2+2"}'
kageko --provider openai --api-key $OPENAI_API_KEY tool search "currency"

# Pipeline generation (UniToolCall-aligned)
kageko --provider openai --api-key $OPENAI_API_KEY pipeline generate-tool "evaluate a math expression" --category analysis --domain science
kageko --provider openai --api-key $OPENAI_API_KEY pipeline generate-skill data-analysis "Analyze CSV files"
kageko --provider openai --api-key $OPENAI_API_KEY pipeline generate-tools-batch specs.json
kageko --provider openai --api-key $OPENAI_API_KEY pipeline generate-data --type single-hop --count 50 --output data/qaoa.jsonl
kageko --provider openai --api-key $OPENAI_API_KEY pipeline list-categories
```

### Available CLIs

| Command | Description |
|---------|-------------|
| `kageko` | Interactive agent REPL and subcommands (chat, tool, skill, session, config, pipeline) |
| `kageko-qaoa synth --output data/qaoa.jsonl` | Generate synthetic QAOA trajectories |
| `kageko-qaoa benchmark --input ref.jsonl --output pred.jsonl --provider openai` | Run benchmark predictions |
| `kageko-qaoa eval --reference ref.jsonl --predicted pred.jsonl` | Strict evaluation (call / turn / conversation metrics) |
| `kageko-qaoa export-sft --input qaoa.jsonl --output sft.jsonl` | Convert QAOA JSONL to SFT format |

## Code Style Guidelines

- **Python version**: 3.13+.
- Every Python module starts with `from __future__ import annotations`.
- Use **dataclasses** with `slots=True, kw_only=True` for all data models and configuration classes.
- Use **type hints** everywhere (function signatures, variables, return types).
- Use `str | None` instead of `Optional[str]` (PEP 604).
- Prefer `pathlib.Path` over `os.path`.
- Docstrings are module-level triple-quoted summaries; inline comments are rare and only used for non-obvious logic.
- Private helpers are prefixed with `_`.
- String formatting: prefer f-strings; use `""".format()` only when necessary.



## Testing Instructions

> **There is currently no test suite in this repository.**

If you add tests, the project convention would suggest:
- Place tests in a top-level `tests/` directory.
- Use `pytest` (not included in dependencies yet).
- Tests should mock LLM adapters to avoid real API calls.

## Security Considerations

- **`bash.run`** invokes `subprocess.run(..., shell=True, cwd=workspace)`. It is restricted to the configured workspace directory.
- **`file.read` / `file.write`** validate paths via `_safe_path()`, ensuring the resolved path stays inside the workspace root. Path traversal with `..` is rejected.
- **`skill.load`** rejects absolute paths and `..` segments; skills must be resolved within configured skill directories.
- **No local echo mode**: the runtime requires a real API key for one of the supported providers.
- API keys are read from environment variables or `.env` files. Never hardcode keys.
- The **MCP client** (`qaoa/adapters/mcp.py`) is currently a placeholder/stub; production use would require proper MCP protocol implementation.

## Runtime Architecture

### Initialization Flow

1. `create_runtime()` loads environment variables (including PowerShell-style `.env` assignments).
2. Selects LLM provider and resolves API key / model / base URL.
3. Registers built-in tools via `BuiltinToolPack`.
4. Optionally sets up ChromaDB RAG tools (`retriever.search`, `retriever.add`).
5. Optionally connects to an MCP server and registers `mcp.*` tools.
6. **Freezes the tool registry** — tools cannot be modified at runtime.
7. Instantiates `QAOAEngine` with the LLM adapter, tools, and optional retriever.

### QAOA Execution Loop (`QAOAEngine.run`)

1. Resolve skill (explicit, active session skill, or LLM-generated if allowed).
2. Plan actions: LLM is asked to return JSON `{"actions":[{"name":"...","input":"..."}]}`.
3. Execute actions via `ToolRegistry.call()` or `retriever.search`.
4. Collect observations.
5. Generate final answer using the query + observations (+ skill context).
6. Return a `QAOATurn` and execution trace.

### CLI Architecture

- `qaoa/cli.py` implements a `typer.Typer` application with subcommands.
- Global options (`--provider`, `--api-key`, `--model`, etc.) are parsed in the callback and shared with subcommands via `typer.Context.obj`.
- The default mode (no subcommand) launches an interactive REPL with `/`-prefixed commands.
- Subcommands include: `chat`, `skill`, `tool`, `session`, `config`, `pipeline`.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `KAGEKO_PROVIDER` | `openai` / `deepseek` / `claude` / `gemini` |
| `OPENAI_API_KEY` | OpenAI API key |
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `CLAUDE_API_KEY` / `ANTHROPIC_API_KEY` | Anthropic API key |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Google API key |
| `KAGEKO_API_KEY` | Fallback generic API key |
| `KAGEKO_MODEL` | Override default model |
| `KAGEKO_BASE_URL` | Custom provider base URL |
| `KAGEKO_WORKSPACE` | Workspace root path |
| `KAGEKO_SKILLS_DIR` | Global skills directory |

The runtime also loads `.env` files (including PowerShell-style `$env:KEY = "value"` assignments).

## Skill Format Conventions

Skills are loaded from `KAGEKO_SKILLS_DIR` and `<workspace>/skills`.

Supported layouts:
1. Single file: `<name>.skill`, `<name>.md`, `<name>.toml`, `<name>.json`, `<name>.yaml`/`.yml`
2. Directory: `<name>/SKILL.md`, `<name>/skill.toml`, etc.

For Markdown skills, YAML frontmatter is supported:

```markdown
---
name: fundamental-analysis
description: Analyze macro and news context for the target symbol.
tools:
  - file.read
  - bash.run
---
# Instructions
...
```

## Deployment Notes

- This is a library / framework, not a service. There is no server process or containerization config.
- Build artifacts:
  - Python: `build/`, `dist/`, `*.egg-info`
