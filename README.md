# KagekoO_O

**English** | [中文](./README_CN.md)

KagekoO_O is a QAOA-oriented agent runtime for building tool-using assistants. The runtime is now designed around a single canonical loop: Query -> Action -> Observation -> Answer.

## What This Is

KagekoO_O provides clear runtime boundaries you can build on:

- A unified runtime entrypoint via create_runtime
- Pluggable LLM adapters
- Workspace-scoped tool execution
- Session memory and context handling
- Structured QAOA turn traces for every response
- Optional RAG and MCP extension modules

## Capability

Integrated modules include:

- Multi-provider LLM adapters: OpenAI, DeepSeek, Claude, Gemini
- ChromaDB-backed retrieval
- In-memory session store
- MCP integration scaffolding
- QAOA action/observation data structures

## Repository Layout

- `qaoa/`: QAOA-native package root
- `qaoa/types.py`: canonical QAOA data models
- `qaoa/learning.py`: dataset generation, JSONL export, strict evaluation
- `qaoa/adapters/`: llm/tools/memory/rag/mcp adapters
- `qaoa/cli.py`: Pure-Python agent CLI (`kageko` command)
- `kageko_qaoa.py`: training/benchmark/evaluation CLI (`kageko-qaoa` command)

## Installation

Requires Python 3.13+.

Recommended for framework development:

	pip install -e .

Optional if you use uv tooling:

	uv pip install -e .

## Quick Start

	from KagekoO_O import AgentMode, create_runtime

	runtime = create_runtime(
		provider="openai",
		model="gpt-4.1-mini",
	)
	response = runtime.run(AgentMode.QAOA, "Summarize the architecture in one paragraph.")
	print(response.answer)

## Agent CLI

The `kageko` command is a pure-Python Typer CLI. No Node.js build step required.

### First-time setup

```bash
kageko config init
```

This saves your provider and API key to `~/.kageko/config.json`. After setup, you never need to pass `--provider` or `--api-key` again.

### Usage

Start REPL:

```bash
kageko
```

One-shot chat:

```bash
kageko chat "Summarize the architecture"
```

List tools:

```bash
kageko tool list
```

Call a tool directly:

```bash
kageko tool call calculator '{"expression": "2+2"}'
```

Generate a new tool from natural language:

```bash
kageko pipeline generate-tool "evaluate a math expression"
```

REPL commands:

- `/session <id>`
- `/skill generate <name> <goal>`
- `/skill use <name>`, `/skill clear`, `/skill active`, `/skill list`
- `/tools list`, `/tools show <name>`, `/tool <name> <payload>`

You can still override credentials per-command if needed:

```bash
kageko --provider deepseek --api-key $DEEPSEEK_API_KEY chat "Hello"
```

QAOA data/eval pipeline CLI:

```bash
# 1) generate synthetic QAOA trajectories
kageko-qaoa synth --output .\data\qaoa_train.jsonl --sft-output .\data\sft_train.jsonl

# 2) run benchmark predictions with your runtime/model
kageko-qaoa benchmark --input .\data\qaoa_train.jsonl --output .\data\pred.jsonl --provider openai

# 3) strict evaluation (call/turn/conversation)
kageko-qaoa eval --reference .\data\qaoa_train.jsonl --predicted .\data\pred.jsonl
```

If `<workspace>/AGENT.md` exists, its content is automatically injected as default
workspace instruction, and can be combined with profile/persona customizations.

## Generated Tools (Frozen Source Code)

All tools are generated through the pipeline. Once generated, they become **immutable source code** in the project:

```bash
# Generate a new tool — it becomes a .py file in tools/
kageko pipeline generate-tool "evaluate a math expression"

# The generated tool is now part of the project source
# It is loaded at runtime and frozen — no modifications allowed at runtime
```

- Generated tools live in `tools/` as Python modules
- They are auto-discovered and registered at runtime startup
- The tool registry is **frozen** after initialization
- To "change" a tool, regenerate it via the pipeline and commit the new source file

This design treats generated tools as version-controlled project artifacts, not runtime-modifiable objects.

## Runtime API

Entrypoint:

	create_runtime(
		provider: str | None = None,
		api_key: str | None = None,
		model: str | None = None,
		base_url: str | None = None,
		workspace: str | None = None,
		skills_dir: str | None = None,
		enable_rag: bool = False,
		rag_persist_dir: str | None = None,
		enable_mcp: bool = False,
		mcp_server_url: str | None = None,
	)

Run interface:

runtime.run(mode, message, session_id=None, tool_plan=None)

`tool_plan` accepts a list of `ToolUse` values as explicit QAOA actions.
When `tool_plan` is omitted, Kageko only uses a skill if one is explicitly activated for the session.
Skill generation happens only when requested (for example via `/skill generate` in the REPL).
Tools are frozen after runtime startup and cannot be adjusted during normal usage.

## Agent Mode

- `AgentMode.QAOA`: unified Query -> Action -> Observation -> Answer execution

When `enable_rag=True`, extra tools (`retriever.search`, `retriever.add`) are registered for QAOA actions.

## Built-in Tools

The default tool pack registers:

- echo
- file.read
- file.write
- bash.run
- todo.write
- skill.load
- skill.describe
- skill.list

Tool file access is restricted to the configured workspace root.

## Skill format compatibility

`skill.load` keeps backward compatibility with `<name>.skill`, and now also supports
mainstream skill layouts:

1. Single-file markdown skill: `<skills_dir>/<name>.md`
2. Directory skill: `<skills_dir>/<name>/SKILL.md`
3. Structured manifests: `.toml`, `.json`, `.yaml`, `.yml`

For markdown skills, YAML frontmatter is supported and aligned with common agent
ecosystem conventions:

```markdown
---
name: fundamental-analysis
description: Analyze macro and news context for the target symbol.
tools:
  - file.read
  - bash.run
---
# Instructions

1. Gather macro indicators.
2. Summarize recent related news.
3. Produce a concise risk-aware fundamental view.
```

`skill.describe` returns normalized JSON metadata for one skill, and `skill.list`
returns the discoverable skills from `KAGEKO_SKILLS_DIR` and `<workspace>/skills`.

## Environment Variables

- KAGEKO_PROVIDER
- OPENAI_API_KEY
- DEEPSEEK_API_KEY
- CLAUDE_API_KEY
- ANTHROPIC_API_KEY
- GEMINI_API_KEY
- GOOGLE_API_KEY
- KAGEKO_API_KEY
- KAGEKO_MODEL
- KAGEKO_BASE_URL
- KAGEKO_WORKSPACE
- KAGEKO_SKILLS_DIR

Local echo mode is intentionally disabled. Configure one provider (`openai`,
`deepseek`, `claude`, or `gemini`) with a valid API key.

The runtime also loads values from .env, including PowerShell-style assignments.

## RAG Setup (QAOA tools)

	runtime = create_runtime(
		provider="openai",
		model="gpt-4.1-mini",
		enable_rag=True,
		rag_persist_dir="./.kageko-rag",
	)

Documents are stored in the `kageko_docs` ChromaDB collection and can be queried via `retriever.search`.

## Extension Modules

Public exports for advanced integration:

- MCPClient, MCPToolAdapter
These are extension surfaces around the QAOA runtime.

## Contributions
Currently this project is just at very beginnig. So all formed contributions are welcomed.
Both a issue and a pr could make this project better.
