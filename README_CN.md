# KagekoO_O

[English](./README.md) | **中文**

KagekoO_O 是一个可组合的智能体运行时框架，用于构建具备工具调用能力的助手和检索增强型工作流。本项目是我在学习智能体与设计模式过程中编写的成果。

## 简介

KagekoO_O 是一个框架层，而非单体应用。它提供了清晰的运行时边界，供开发者在此基础上进行构建：

- 通过 `create_runtime` 提供统一的运行时入口
- 可插拔的大语言模型（LLM）适配器
- 工作区范围内的工具执行
- 会话记忆与上下文管理
- 可选的 RAG、MCP、A2A 和强化学习（RL）扩展模块

## 功能

- **chat**：直接生成响应
- **react**：工具-观察驱动的响应
- **reflect**：草稿与精炼循环
- **plan_execute**：先规划后生成答案
- **rag**：检索增强型回答

已集成的模块包括：

- LLM API 适配器（目前仅支持 OpenAI 及兼容 OpenAI 的 API）
- ChromaDB 向量检索
- 内存会话存储
- MCP 集成脚手架
- A2A 编排脚手架
- 强化学习策略与回合原语

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
	response = runtime.run(AgentMode.CHAT, "用一段话概括该架构。")
	print(response.text)

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

`tool_plan` 接受一个 `ToolUse` 值列表，用于在 react 模式下显式指定工具调用。

## 智能体模式

- `AgentMode.CHAT`：直接生成
- `AgentMode.REACT`：工具辅助推理
- `AgentMode.REFLECT`：基于修订的响应
- `AgentMode.PLAN_EXECUTE`：先规划后回答
- `AgentMode.RAG`：检索上下文后再生成

RAG 模式需要设置 `enable_rag=True` 以启用检索器。

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
- `KAGEKO_API_KEY`
- `KAGEKO_MODEL`
- `KAGEKO_BASE_URL`
- `KAGEKO_WORKSPACE`
- `KAGEKO_SKILLS_DIR`

运行时也会从 `.env` 文件中加载配置，包括 PowerShell 风格的赋值语句。

## RAG 配置

	runtime = create_runtime(
		provider="openai",
		model="gpt-4.1-mini",
		enable_rag=True,
		rag_persist_dir="./.kageko-rag",
	)

文档存储在 ChromaDB 的 `kageko_docs` 集合中。

## 扩展模块

高级集成的公开导出：

- `MCPClient`、`MCPToolAdapter`
- `A2AOrchestrator`、`AgentRegistry`
- `RLAgent`、`AgentPolicy`、`Episode`

这些是扩展接口，而非单一默认应用管道。

## 贡献

目前本项目仍处于非常早期的阶段，欢迎任何形式的贡献。
无论是提交 Issue 还是 Pull Request，都能帮助本项目变得更好。
