# KagekoO_O

[English](./README.md) | **中文**

KagekoO_O 是一个面向 QAOA 的智能体运行时，用于构建具备工具调用能力的助手。核心循环 **Query → Action → Observation → Answer** 以及技能生成流水线均基于 [UniToolCall](https://arxiv.org/abs/2604.11557)（arXiv:2604.11557）。支持原生函数调用、流式输出、迭代式智能体执行以及多层权限系统。

## 简介

- 通过 `create_runtime` 提供统一入口
- 可插拔 LLM 适配器，支持原生工具调用（OpenAI、DeepSeek、Claude、Gemini）
- 流式响应与实时终端渲染
- 技能系统：生成、转换、目录式存储
- 多层权限管线（验证 → 规则 → 提示 → 会话记忆）
- 迭代式 QAOA 引擎，支持上下文压缩与错误恢复
- 工作区范围内的工具执行
- 会话记忆，支持恢复/派生
- 基于 prompt_toolkit 的 Tab 补全 REPL

## 仓库结构

```
KagekoO_O/
├── qaoa/
│   ├── engine.py          # 迭代式 QAOA 循环，原生函数调用
│   ├── runtime.py         # create_runtime() 工厂
│   ├── types.py           # 核心数据模型（SkillSpec、QAOATurn 等）
│   ├── streaming.py       # StreamEvent、ConsoleStreamRenderer
│   ├── permissions.py     # 多层权限管线
│   ├── compact.py         # 上下文自动压缩
│   ├── tasks.py           # 持久化任务面板，支持依赖关系
│   ├── context.py         # 工作区上下文加载
│   ├── learning.py        # 数据集生成、JSONL 导出、评测
│   ├── adapters/
│   │   ├── llm.py         # LLM 适配器（流式 + 原生工具）
│   │   ├── memory.py      # 会话存储（恢复/派生）
│   │   ├── rag.py         # ChromaDB 向量存储
│   │   └── mcp.py         # MCP 客户端（占位）
│   ├── tools/
│   │   ├── registry.py    # ToolRegistry + ToolSpec
│   │   └── builtins.py    # 注册所有内置工具
│   ├── skills/
│   │   ├── registry.py    # SkillRegistry
│   │   ├── loader.py      # SkillLoader（Markdown、TOML、JSON、YAML）
│   │   ├── convert.py     # Claude Code / Superpowers → Kageko 转换器
│   │   └── generator.py   # SkillGenerator（QAOA UniToolCall 格式）
│   ├── agents/
│   │   ├── subagent.py    # 子智能体执行
│   │   └── registry.py    # 智能体定义
│   ├── cli/
│   │   ├── app.py         # Typer CLI 应用
│   │   ├── repl.py         # REPL 调度器（Tab 补全）
│   │   ├── render.py       # Rich 表格/面板渲染
│   │   └── setup.py        # 设置向导
│   ├── daemon/             # JSON-RPC 守护进程
│   ├── pipeline/           # QAOA 数据生成流水线
│   └── mcp/                # MCP 协议客户端
├── test/                   # 外部测试工作区
└── pyproject.toml
```

## 安装

需要 Python 3.13+。

```bash
uv pip install -e .
```

## 快速开始

```python
from KagekoO_O import AgentMode, create_runtime

runtime = create_runtime(
    provider="openai",
    model="gpt-4.1-mini",
)
response = runtime.run(AgentMode.QAOA, "用一段话概括该架构。")
print(response.answer)
```

## Agent CLI

```bash
# 首次设置
kageko config init

# 交互式 REPL（Tab 补全）
kageko

# 流式单次对话
kageko chat --stream "读取 AGENTS.md 并总结"

# 阻塞式单次对话
kageko chat "什么是 QAOA？"

# 列出工具
kageko tool list

# 技能管理
kageko skill list
kageko skill import ./external-skills/ --format claude-code

# 会话管理
kageko session list
```

### REPL 指令

| 指令 | 说明 |
|---------|-------------|
| `/help` | 显示所有命令 |
| `/session` | 列出会话，按编号或 ID 切换 |
| `/session new` | 创建新会话 |
| `/skill list` | 列出已注册技能 |
| `/skill generate <name> <goal>` | 生成 QAOA 技能 |
| `/skill use <name>` | 激活技能 |
| `/skill import <path> --format <fmt>` | 导入外部技能 |
| `/tools list` | 列出所有工具 |
| `/mode <default\|auto\|plan>` | 切换权限模式 |
| `/search <query>` | 搜索工具 |
| `/exit` | 退出 |

输入 `/` + Tab 可查看所有命令及补全。

## 内置工具

| 工具 | 类别 | 风险 | 说明 |
|------|----------|------|-------------|
| `echo` | system | read | 回显文本 |
| `file.read` | search | read | 读取工作区及绝对路径文件 |
| `file.write` | operations | write | 写入文件（自动识别技能格式） |
| `bash.run` | operations | destructive | 命令行执行 |
| `todo.write` | operations | write | 添加 TODO |
| `todo.done` | operations | write | 标记 TODO 完成 |
| `skill.load` | search | read | 加载技能内容 |
| `skill.describe` | search | read | 技能 JSON 元数据 |
| `skill.list` | search | read | 列出可发现技能 |
| `skill.generate` | generate | read | 生成 QAOA UniToolCall 技能 |

## 技能系统

技能以目录形式存储，包含 `SKILL.md` 清单、可执行脚本和参考文档：

```
skills/<name>/
├── SKILL.md              ← QAOA UniToolCall 技能清单
├── scripts/              ← 可执行工具（每个脚本一个原子操作）
│   ├── step1.sh
│   └── step2.py
└── reference/            ← 面向人类的参考文档
    └── README.md
```

### SKILL.md 格式

YAML Frontmatter 包含 QAOA UniToolCall 元数据：

```markdown
---
name: project-scaffolder
description: 创建 Python CLI 项目骨架
category: operations
domain: technology
tools:
  - file.write
  - bash.run
  - project-scaffolder.create_dirs
  - project-scaffolder.write_cli
permissions:
  - read
  - write
---

# Skill: project-scaffolder

## Objective
创建标准化的 Python CLI 项目布局。

## Tools
- project-scaffolder.create_dirs: 创建 src/ 目录结构
- project-scaffolder.write_cli: 写入带 Typer 应用的 cli.py

## Steps
1. 创建项目目录
2. 写入 pyproject.toml
3. 写入 __init__.py
4. 写入 cli.py
5. 用 bash.run 验证

## Safety
仅在工作区内写入。
```

### 脚本即 UniTool 工具

`scripts/` 中的每个脚本在技能激活时成为临时工具。一个脚本 = 一个原子 UniToolCall 操作。工具在激活时注册，取消激活时移除。技能的 `tools:` 字段将它们与内置工具一并列出，让 LLM 获得完整的能力视图。

```bash
# 激活前：10 个工具
kageko tool list

# /skill use project-scaffolder → 14 个工具（4 个脚本工具）
# /skill clear → 回到 10 个工具
```

### 技能生成

`skill.generate` 产出完整的 QAOA UniToolCall 技能文档。名称保持不变（"brainstorming" 不会变成其他名字）。工具列表包含 `file.read`（探索）、`bash.run`（执行）、`file.write`（输出）。生成后可添加脚本和参考文档以扩展能力。

### 技能转换

从其他智能体生态导入：

```bash
kageko skill import ./external-skills/ --format claude-code
```

## 权限系统

多层管线：验证输入 → 只读自动通过 → 危险模式检测 → 用户规则 → 模式检查 → 会话记忆 → 交互式提示。

模式：`default`（写入需确认）、`auto`（全部自动批准）、`plan`（只读）、`bypass`（跳过提示）。

## 流式输出

```bash
kageko chat --stream "读取 SPEC.md 并构建项目"
```

文本 Token 实时显示，工具调用内联展示结果。

## 测试工作区

项目外的 `test/` 目录包含用于端到端测试的外部工作区：

```bash
cd test
kageko
```

测试任务覆盖完整流程：读取 SPEC → 从磁盘发现外部 Superpowers 技能 → 通过 `skill.generate` 转换为 Kageko QAOA UniToolCall 格式 → 应用生成的技能构建项目 → 验证。

## 环境变量

- `KAGEKO_PROVIDER` / `KAGEKO_API_KEY` / `KAGEKO_MODEL`
- `KAGEKO_BASE_URL` / `KAGEKO_WORKSPACE` / `KAGEKO_SKILLS_DIR`
- `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` / `CLAUDE_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY`

## QAOA 数据流水线

```bash
kageko pipeline generate-data --type single-hop --count 50 --output data/qaoa_single.jsonl
kageko pipeline generate-data --type multi-hop --count 20 --output data/qaoa_multi.jsonl
kageko pipeline generate-data --type multi-turn --count 10 --output data/qaoa_multiturn.jsonl

kageko-qaoa synth --output data/qaoa_train.jsonl --sft-output data/sft_train.jsonl
kageko-qaoa benchmark --input data/qaoa_train.jsonl --output data/pred.jsonl --provider openai
kageko-qaoa eval --reference data/qaoa_train.jsonl --predicted data/pred.jsonl
```

## 贡献

目前仍处于早期阶段，欢迎提交 Issue 和 PR。
