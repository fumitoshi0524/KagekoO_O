# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Reference

AGENTS.md in the workspace root contains the comprehensive project guide (architecture, code style, security, skill formats, env vars). Read it for full context. This file covers only what's specific to Claude Code workflows.

## Quick Commands

```bash
# Editable install (required before running)
uv pip install -e .

# Interactive REPL
kageko

# One-shot chat
kageko chat "Summarize the architecture"

# First-time setup (saves provider + API key to ~/.kageko/config.json)
kageko config init

# Tool management
kageko tool list
kageko tool show calculator
kageko tool call calculator '{"expression": "2+2"}'
kageko tool search "currency"          # fuzzy search by name/description/category/domain

# Pipeline: generate tools/skills from natural language
kageko pipeline generate-tool "search stock prices by symbol" --name stock_search --category search --domain finance
kageko pipeline generate-skill data-analysis "Analyze CSV files"
kageko pipeline generate-tools-batch specs.json --output-dir ./tools   # batch from JSON spec file
kageko pipeline list-categories                                       # show UniToolCall categories/domains

# QAOA data generation (UniToolCall-aligned)
kageko pipeline generate-data --type single-hop --count 50 --output data/qaoa_single.jsonl
kageko pipeline generate-data --type multi-hop --count 20 --output data/qaoa_multi.jsonl
kageko pipeline generate-data --type multi-turn --count 10 --output data/qaoa_multiturn.jsonl

# QAOA data/eval pipeline
kageko-qaoa synth --output data/qaoa_train.jsonl --sft-output data/sft_train.jsonl
kageko-qaoa benchmark --input data/qaoa_train.jsonl --output data/pred.jsonl --provider openai
kageko-qaoa eval --reference data/qaoa_train.jsonl --predicted data/pred.jsonl
kageko-qaoa export-sft --input data/qaoa_train.jsonl --output data/sft_train.jsonl
```

## Key Architecture Decisions

**UniToolCall alignment**: Tools follow the UniToolCall standard (arXiv:2604.11557) with 6 functional categories (`analysis`, `operations`, `system`, `visualization`, `search`, `generate`) and 13 application domains. `ToolSpec` carries `category` and `domain` fields.

**Tool registry is frozen at startup.** Generated tools live in `tools/` and are auto-loaded at runtime via `GeneratedToolPack`. Once frozen, no tool modifications are possible. To change a tool, regenerate it via the pipeline and commit the new source file.

**Provider selection is automatic** when not explicit: it checks env vars in priority order (KAGEKO_PROVIDER, then individual keys for DeepSeek->Claude->Gemini, falling back to OpenAI).

**PowerShell-style .env** (`$env:KEY = "value"`) is supported alongside standard `.env` format, because Windows users commonly write env files this way.

**Workspace context injection**: `ContextManager` loads `AGENTS.md` (or `AGENT.md`) from the workspace root and injects it into every agent query. Git status is also injected automatically.

**Skill resolution order**: explicit CLI skill name -> session's active skill -> none (unless `allow_skill_generation=True` is passed, which triggers LLM-based skill generation).

**Generated tools (32 built-in)**: The `tools/` directory contains production-quality tool modules covering all 6 UniToolCall categories and 13 domains. Each tool is a self-contained Python module with a `run(payload: str) -> str` function and a `TOOL_SPEC` dict.

**No test suite exists yet.** If adding tests, use `pytest`, place in `tests/`, and mock LLM adapters.

## Python Conventions

- `from __future__ import annotations` in every module
- Dataclasses with `slots=True, kw_only=True` for data models
- PEP 604 union syntax (`str | None`, not `Optional[str]`)
- `pathlib.Path`, not `os.path`
- Python 3.13+ required
