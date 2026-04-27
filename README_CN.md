# KagekoO_O

[English](./README.md) | **中文**

KagekoO_O 是一个面向 QAOA 的智能体运行时，用于构建具备工具调用能力的助手。运行时核心统一为 Query -> Action -> Observation -> Answer。

## 简介

KagekoO_O 提供了清晰的运行时边界，供开发者在此基础上进行构建：

- 通过 `create_runtime` 提供统一的运行时入口
- 可插拔的大语言模型（LLM）适配器
- 工作区范围内的工具执行
- 会话记忆与上下文管理
- 每次响应都输出结构化 QAOA 回合轨迹
- 可选的 RAG 与 MCP 扩展模块

## 能力

已集成的模块包括：

- 多提供商 LLM 适配器：OpenAI、DeepSeek、Claude、Gemini
- ChromaDB 向量检索
- 内存会话存储
- MCP 集成脚手架
- QAOA action/observation 数据结构

## 仓库结构

- `qaoa/`：QAOA 原生包根目录
- `qaoa/types.py`：统一 QAOA 数据模型
- `qaoa/learning.py`：数据集生成、JSONL 导出、严格评测
- `qaoa/adapters/`：llm/tools/memory/rag/mcp 适配层
- `qaoa/cli.py`：纯 Python Agent CLI（`kageko` 命令）
- `kageko_qaoa.py`：训练/基准/评测 CLI（`kageko-qaoa` 命令）

## 安装

需要 Python 3.13+。

推荐用于框架开发：

	pip install -e .

若使用 uv 工具链，可选：

	uv pip install -e .

## 快速开始

	from KagekoO_O import AgentMode, create_runtime

	runtime = create_runtime(
		provider="openai",
		model="gpt-4.1-mini",
	)
	response = runtime.run(AgentMode.QAOA, "用一段话概括该架构。")
	print(response.answer)

## Agent CLI

`kageko` 命令是基于 Typer 的纯 Python CLI，无需 Node.js 构建步骤。

### 首次设置

```bash
kageko config init
```

将你的 provider 和 API key 保存到 `~/.kageko/config.json`。设置完成后，无需再传递 `--provider` 或 `--api-key`。

### 使用

启动 REPL：

```bash
kageko
```

单次对话：

```bash
kageko chat "用一段话概括架构"
```

列出工具：

```bash
kageko tool list
```

直接调用工具：

```bash
kageko tool call calculator '{"expression": "2+2"}'
```

通过自然语言生成新工具：

```bash
kageko pipeline generate-tool "evaluate a math expression"
```

REPL 指令：

- `/session <id>`
- `/skill generate <name> <goal>`
- `/skill use <name>`、`/skill clear`、`/skill active`、`/skill list`
- `/tools list`、`/tools show <name>`、`/tool <name> <payload>`

如需临时覆盖凭证：

```bash
kageko --provider deepseek --api-key $DEEPSEEK_API_KEY chat "Hello"
```

QAOA 数据与评测流水线 CLI：

```bash
# 1) 生成合成 QAOA 轨迹
kageko-qaoa synth --output .\data\qaoa_train.jsonl --sft-output .\data\sft_train.jsonl

# 2) 用当前 runtime/model 跑基准预测
kageko-qaoa benchmark --input .\data\qaoa_train.jsonl --output .\data\pred.jsonl --provider openai

# 3) 严格评测（函数调用/回合/会话）
kageko-qaoa eval --reference .\data\qaoa_train.jsonl --predicted .\data\pred.jsonl
```

若 `<workspace>/AGENT.md` 存在，会自动作为默认工作区指令注入，并可与
profile/persona 自定义叠加使用。

## 生成工具（冻结的源代码）

所有工具均通过 pipeline 生成。生成后，它们成为项目中的**不可变源代码**：

```bash
# 生成新工具 —— 它会变成 tools/ 目录下的一个 .py 文件
kageko pipeline generate-tool "evaluate a math expression"

# 生成的工具现在是项目源码的一部分
# 它在运行时被加载并冻结 —— 不允许在运行时修改
```

- 生成的工具位于 `tools/` 目录下，以 Python 模块形式存在
- 它们在运行时启动时被自动发现并注册
- 工具注册表在初始化后**冻结**
- 要"修改"工具，需通过 pipeline 重新生成并提交新的源文件

这种设计将生成的工具视为版本控制的项目产物，而非可在运行时修改的对象。

## 运行时 API

入口函数：

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

运行接口：

runtime.run(mode, message, session_id=None, tool_plan=None)

`tool_plan` 接受 `ToolUse` 列表，作为显式 QAOA action 输入。
当不传 `tool_plan` 时，Kageko 仅在会话中存在已激活 skill 时使用该 skill。
skill 只在被明确请求时生成（例如 REPL 中的 `/skill generate`）。
工具集会在运行时启动后冻结，正常使用阶段不可动态调整。

## 智能体模式

- `AgentMode.QAOA`：统一执行 Query -> Action -> Observation -> Answer

当 `enable_rag=True` 时，会额外注册 `retriever.search` 与 `retriever.add` 两个 QAOA 工具。

## 内置工具

默认工具包注册了以下工具：

- `echo`
- `file.read`
- `file.write`
- `bash.run`
- `todo.write`
- `skill.load`
- `skill.describe`
- `skill.list`

工具的文件访问权限限制在已配置的工作区根目录内。

## Skill 格式兼容（对齐主流用法）

`skill.load` 继续兼容旧格式 `<name>.skill`，并新增支持主流 skill 组织方式：

1. 单文件 Markdown：`<skills_dir>/<name>.md`
2. 目录式 Skill：`<skills_dir>/<name>/SKILL.md`
3. 结构化清单：`.toml`、`.json`、`.yaml`、`.yml`

对于 Markdown Skill，支持 YAML Frontmatter（与常见 agent 生态格式一致）：

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

`skill.describe` 会返回单个 skill 的标准化 JSON 元数据，`skill.list` 会列出
`KAGEKO_SKILLS_DIR` 与 `<workspace>/skills` 下可发现的 skill。

## 环境变量

- `KAGEKO_PROVIDER`
- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `CLAUDE_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`
- `KAGEKO_API_KEY`
- `KAGEKO_MODEL`
- `KAGEKO_BASE_URL`
- `KAGEKO_WORKSPACE`
- `KAGEKO_SKILLS_DIR`

本框架已禁用本地 echo 模式，必须配置 `openai`、`deepseek`、`claude`、`gemini`
之一并提供有效 API Key。

运行时也会从 `.env` 文件中加载配置，包括 PowerShell 风格的赋值语句。

## RAG 配置（QAOA 工具）

	runtime = create_runtime(
		provider="openai",
		model="gpt-4.1-mini",
		enable_rag=True,
		rag_persist_dir="./.kageko-rag",
	)

文档存储在 ChromaDB 的 `kageko_docs` 集合中，并可通过 `retriever.search` 查询。

## 扩展模块

高级集成的公开导出：

- `MCPClient`、`MCPToolAdapter`
这些是围绕 QAOA 运行时的扩展接口。

## 贡献

目前本项目仍处于非常早期的阶段，欢迎任何形式的贡献。
无论是提交 Issue 还是 Pull Request，都能帮助本项目变得更好。
