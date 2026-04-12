# KagekoO_O

**English** | [中文](./README_CN.md)

KagekoO_O is a composable agent runtime for building tool-using assistants and retrieval-augmented workflows, which is what I've written during my agent and design pattern learning progress.

## What This Is

KagekoO_O is a framework layer, not a monolithic app. It provides clear runtime boundaries you can build on:

- A unified runtime entrypoint via create_runtime
- Pluggable LLM adapters
- Workspace-scoped tool execution
- Session memory and context handling
- Optional RAG, MCP, A2A, and RL extension modules

## Capabilities

- chat: direct response generation
- react: tool-observation-driven response
- reflect: draft and refinement loop
- plan_execute: planning before final answer
- rag: retrieval-augmented answering

Integrated modules include:

- LLM API adapter (currently only for openai & openai compatible api)
- ChromaDB-backed retrieval
- In-memory session store
- MCP integration scaffolding
- A2A orchestration scaffolding
- RL policy and episode primitives

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
	response = runtime.run(AgentMode.CHAT, "Summarize the architecture in one paragraph.")
	print(response.text)

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

tool_plan accepts a list of ToolUse values for explicit calls in react mode.

## Agent Modes

- AgentMode.CHAT: direct generation
- AgentMode.REACT: tool-assisted reasoning
- AgentMode.REFLECT: revision-based response
- AgentMode.PLAN_EXECUTE: plan-then-answer pattern
- AgentMode.RAG: retrieve context before generation

RAG mode requires enable_rag=True so a retriever is available.

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
- KAGEKO_API_KEY
- KAGEKO_MODEL
- KAGEKO_BASE_URL
- KAGEKO_WORKSPACE
- KAGEKO_SKILLS_DIR

The runtime also loads values from .env, including PowerShell-style assignments.

## RAG Setup

	runtime = create_runtime(
		provider="openai",
		model="gpt-4.1-mini",
		enable_rag=True,
		rag_persist_dir="./.kageko-rag",
	)

Documents are stored in the kageko_docs ChromaDB collection.

## Extension Modules

Public exports for advanced integration:

- MCPClient, MCPToolAdapter
- A2AOrchestrator, AgentRegistry
- RLAgent, AgentPolicy, Episode

These are extension surfaces, not a single default application pipeline.

## Contributions
Currently this project is just at very beginnig. So all formed contributions are welcomed.
Both a issue and a pr could make this project better.
