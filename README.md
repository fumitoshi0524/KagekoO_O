# KagekoO_O

**English** | [中文](./README_CN.md)

KagekoO_O is a QAOA-oriented agent runtime for building tool-using assistants. The runtime is built around a single canonical loop: **Query → Action → Observation → Answer**, with native function calling, streaming, and an iterative agentic execution model.

## What This Is

- A unified runtime entrypoint via `create_runtime`
- Pluggable LLM adapters with native tool calling (OpenAI, DeepSeek, Claude, Gemini)
- Streaming response support with real-time console rendering
- Skill system with generation, conversion, and directory-based storage
- Multi-layer permission pipeline (validate → rules → prompt → session memory)
- Iterative QAOA engine with context compaction and error recovery
- Workspace-scoped tool execution
- Session memory with resume/fork support
- Tab-completion REPL via prompt_toolkit

## Repository Layout

```
KagekoO_O/
├── qaoa/
│   ├── engine.py          # Iterative QAOA loop with native function calling
│   ├── runtime.py         # create_runtime() factory
│   ├── types.py           # Core data models (SkillSpec, QAOATurn, etc.)
│   ├── streaming.py       # StreamEvent, ConsoleStreamRenderer
│   ├── permissions.py     # Multi-layer permission pipeline
│   ├── compact.py         # Context auto-compaction
│   ├── tasks.py           # Persistent task board with DAG dependencies
│   ├── context.py         # Workspace context loader
│   ├── learning.py        # Dataset generation, JSONL export, evaluation
│   ├── adapters/
│   │   ├── llm.py         # LLM adapters (streaming + native tools)
│   │   ├── memory.py      # Session store with resume/fork
│   │   ├── rag.py         # ChromaDB vector store
│   │   └── mcp.py         # MCP client (stub)
│   ├── tools/
│   │   ├── registry.py    # ToolRegistry + ToolSpec
│   │   └── builtins.py    # Register all built-in tools
│   ├── skills/
│   │   ├── registry.py    # SkillRegistry
│   │   ├── loader.py      # SkillLoader (markdown, TOML, JSON, YAML)
│   │   ├── convert.py     # Claude Code / Superpowers → Kageko converter
│   │   └── generator.py   # SkillGenerator (QAOA UniToolCall format)
│   ├── agents/
│   │   ├── subagent.py    # Sub-agent execution
│   │   └── registry.py    # Agent definitions (general, explore, plan)
│   ├── cli/
│   │   ├── app.py         # Typer CLI app
│   │   ├── repl.py         # REPL dispatcher with tab completion
│   │   ├── render.py       # Rich table/panel renderers
│   │   └── setup.py        # Setup wizard
│   ├── daemon/             # JSON-RPC daemon
│   ├── pipeline/           # QAOA data generation pipeline
│   └── mcp/                # MCP protocol client
├── test/                   # External test workspace (see below)
└── pyproject.toml
```

## Installation

Requires Python 3.13+.

```bash
uv pip install -e .
```

## Quick Start

```python
from KagekoO_O import AgentMode, create_runtime

runtime = create_runtime(
    provider="openai",
    model="gpt-4.1-mini",
)
response = runtime.run(AgentMode.QAOA, "Summarize the architecture in one paragraph.")
print(response.answer)
```

## Agent CLI

```bash
# First-time setup
kageko config init

# Interactive REPL with tab completion
kageko

# One-shot chat with streaming
kageko chat --stream "Read AGENTS.md and summarize"

# One-shot chat (blocking)
kageko chat "What is QAOA?"

# List available tools
kageko tool list

# Manage skills
kageko skill list
kageko skill import ./external-skills/ --format claude-code

# Sessions
kageko session list
```

### REPL Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/session` | List sessions, switch by number or ID |
| `/session new` | Create new session |
| `/skill list` | List registered skills |
| `/skill generate <name> <goal>` | Generate a QAOA skill |
| `/skill use <name>` | Activate a skill |
| `/skill import <path> --format <fmt>` | Import external skills |
| `/tools list` | List all tools |
| `/mode <default\|auto\|plan>` | Switch permission mode |
| `/search <query>` | Search tools |
| `/exit` | Quit |

Tab-completion is available for all commands. Type `/` + Tab to see options.

## Built-in Tools

| Tool | Category | Risk | Description |
|------|----------|------|-------------|
| `echo` | system | read | Echo back text |
| `file.read` | search | read | Read workspace files + absolute paths |
| `file.write` | operations | write | Write files (auto-detects skill format) |
| `bash.run` | operations | destructive | Shell execution (Git Bash / WSL / cmd) |
| `todo.write` | operations | write | Append TODO item |
| `todo.done` | operations | write | Mark TODO as complete |
| `skill.load` | search | read | Load skill content |
| `skill.describe` | search | read | Skill metadata as JSON |
| `skill.list` | search | read | List discoverable skills |
| `skill.generate` | generate | read | Generate QAOA UniToolCall skill |

## Skills

Skills are stored as directories with `SKILL.md` inside:

```
skills/
├── brainstorming/
│   └── SKILL.md
├── test-driven-development/
│   └── SKILL.md
└── ...
```

Each skill has YAML frontmatter with QAOA UniToolCall metadata:

```markdown
---
name: brainstorming
description: Explore user intent before implementation
category: analysis
domain: technology
tools:
  - file.read
  - bash.run
permissions:
  - read
---

# Skill: brainstorming

## Objective
Turn ideas into fully formed designs.

## Steps
1. Explore project context
2. Ask clarifying questions
3. Propose approaches
4. Present design
```

### Skill Conversion

Import skills from other agent ecosystems:

```bash
# Convert Claude Code / Superpowers skills to Kageko QAOA format
kageko skill import ./superpowers-skills/ --format claude-code
```

### Skill Generation

Skills are generated on-demand via `skill.generate`. The LLM reads a skill description and produces a complete QAOA UniToolCall skill document with proper YAML frontmatter, category, domain, tools, and step-by-step instructions.

## Permission System

Multi-layer pipeline: validate input → read-only auto-approve → dangerous pattern detection → user rules → mode check → session memory → interactive prompt.

Modes: `default` (prompt for writes), `auto` (auto-approve all), `plan` (read-only), `bypass` (skip prompts).

## Streaming

```bash
kageko chat --stream "Read SPEC.md and build the project"
```

Text tokens appear in real-time. Tool calls show inline with results.

## Test Workspace

The `test/` directory (outside the project) contains an external workspace for end-to-end testing:

```bash
cd test
kageko
```

A test task that exercises the full pipeline:

1. Read SPEC.md
2. Discover external superpowers skills from disk
3. Convert them to Kageko QAOA UniToolCall format via `skill.generate`
4. Apply the generated skill to build a project (e.g., a CLI tool)
5. Verify with `bash.run`

Example SPEC that was successfully executed (9 turns, 0 errors):

```
Read the brainstorming superpowers skill from disk →
skill.generate to convert to QAOA format →
use the skill to design hello.py →
write hello.py →
test with bash.run
```

## Environment Variables

- `KAGEKO_PROVIDER` / `KAGEKO_API_KEY` / `KAGEKO_MODEL`
- `KAGEKO_BASE_URL` / `KAGEKO_WORKSPACE` / `KAGEKO_SKILLS_DIR`
- `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` / `CLAUDE_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY`

## QAOA Data Pipeline

```bash
kageko pipeline generate-data --type single-hop --count 50 --output data/qaoa_single.jsonl
kageko pipeline generate-data --type multi-hop --count 20 --output data/qaoa_multi.jsonl
kageko pipeline generate-data --type multi-turn --count 10 --output data/qaoa_multiturn.jsonl

kageko-qaoa synth --output data/qaoa_train.jsonl --sft-output data/sft_train.jsonl
kageko-qaoa benchmark --input data/qaoa_train.jsonl --output data/pred.jsonl --provider openai
kageko-qaoa eval --reference data/qaoa_train.jsonl --predicted data/pred.jsonl
```

## Contributions

Currently at early stage. Issues and PRs welcome.
