# Kageko

Three-in-one AI agent: coding, general-purpose, research.  
[中文](README.zh.md)

---
![1](docs/screenshots/1.png)
---

## Features

- **Multi-provider** — OpenAI, DeepSeek (including reasoner), Ollama, and any OpenAI-compatible API
- **Interactive CLI** — Rich-based chat with streaming, tool cards, and arrow-key permission menus
- **TUI** — Full Textual terminal UI for multi-panel agent interaction
- **Tool system** — File I/O, shell execution, grep, AST analysis, hashline editing, MCP client
- **Subagent delegation** — Spawn isolated subagents for parallel tasks
- **QAOA mode** — Question-Action-Observation-Answer trajectory for research
- **Memory & skills** — FTS5-backed persistent memory, skill extraction from conversations
- **Context compression** — 3-layer strategy: tool pruning → image stripping → LLM summarization
- **Guardrails** — Rule engine for dangerous commands, failure tracking, idempotency detection
- **Security modes** — Permissive, Read-only, Interactive (with session-wide "always allow")

## Quick Start

```bash
git clone https://github.com/your-org/kageko.git
cd kageko
pip install -e .

# Setup wizard
kageko setup

# Start chatting
kageko chat

# Single query
kageko chat "explain this codebase"

# TUI mode
kageko tui
```

## Configuration

Edit `~/.kageko/kageko.toml` (created by `kageko setup`):

```toml
[agent]
model = "deepseek-chat"       # or gpt-4o, deepseek-reasoner, llama3
mode = "tool-use"              # tool-use | qaoa
max_turns = 20
provider = "deepseek"          # openai | deepseek | ollama

[security]
mode = "interactive"           # permissive | read-only | interactive

[database]
path = "~/.kageko/kageko.db"

[logging]
level = "INFO"
```

Environment variables (override TOML):
- `KAGEKO_API_KEY` — API key
- `KAGEKO_MODEL` — Model name
- `KAGEKO_BASE_URL` — API base URL
- Provider-specific: `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`

## Providers

| Provider | Models | Notes |
|----------|--------|-------|
| `openai` | gpt-4o, gpt-4o-mini | Default |
| `deepseek` | deepseek-chat, deepseek-reasoner | reasoner: no tools/temperature |
| `ollama` | llama3, ... | Local; set `base_url` |

## Project Structure

```
KagekoO_O/
├── src/kageko/
│   ├── cli.py              # CLI entry: chat, tui, setup, version
│   ├── config.py           # TOML + env config loading
│   ├── types.py            # Message, ToolCall, StreamToken, AgentResult
│   ├── agent/
│   │   ├── loop.py         # AgentEngine: run, run_stream
│   │   ├── context.py      # Context compression
│   │   ├── permissions.py  # Security pipeline
│   │   ├── guardrails.py   # Rule engine
│   │   ├── delegate.py     # Subagent spawning
│   │   └── ttsr.py         # Stream interceptor
│   ├── llm/
│   │   ├── adapter.py      # OpenAI-compatible LLM client
│   │   └── providers.py    # Provider profiles & model info
│   ├── tools/
│   │   ├── registry.py     # Tool registry
│   │   ├── builtin/        # file, shell, grep, AST, hashline
│   │   └── mcp_client.py   # MCP protocol client
│   ├── data/
│   │   └── db.py           # SQLite + FTS5 database
│   ├── learning/
│   │   ├── memory.py       # Memory manager
│   │   ├── skills.py       # Skill engine
│   │   └── curator.py      # Maintenance
│   ├── repl/               # CLI rendering: stream, diff, prompt, tool cards
│   ├── tui/                # Textual TUI application
│   └── gateway/            # Multi-platform message gateway (WIP)
├── kageko.toml             # Project-level config example
├── pyproject.toml
└── docs/
```

## Acknowledgements

Kageko's design draws inspiration from prior work in agent architecture and tool-use:

- **Hermes** — agent framework with multi-platform gateway and persistent learning loop
- **OMP (Open Modular Platform)** — modular agent composition and cross-provider model routing
- **Unitool Call** — unified tool-calling protocol across heterogeneous LLM backends

## License

MIT — see [LICENSE](LICENSE) for full text.
