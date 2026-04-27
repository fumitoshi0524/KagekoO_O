"""Compatibility public API module for distribution installs."""

from qaoa.types import (
    APPLICATION_DOMAINS,
    FUNCTIONAL_CATEGORIES,
    AgentMode,
    AgentRequest,
    AgentResponse,
    QAOAAction,
    QAOASkill,
    QAOAObservation,
    QAOATurn,
    ToolUse,
)
from qaoa.learning import (
    QAOAEvalMetrics,
    evaluate_qaoa_predictions,
    export_conversations_jsonl,
    export_qaoa_jsonl,
    export_sft_jsonl,
    load_conversations_jsonl,
    load_qaoa_jsonl,
    load_toolset_json,
    synthesize_qaoa_turns,
)
from qaoa.adapters.mcp import MCPClient, MCPToolAdapter
from qaoa.adapters.rag import VectorStore
from qaoa.runtime import KagekoRuntime, create_runtime

__all__: list[str] = [
    "AgentMode",
    "AgentRequest",
    "AgentResponse",
    "FUNCTIONAL_CATEGORIES",
    "APPLICATION_DOMAINS",
    "QAOAAction",
    "QAOASkill",
    "QAOAObservation",
    "QAOATurn",
    "QAOAEvalMetrics",
    "ToolUse",
    "KagekoRuntime",
    "create_runtime",
    "VectorStore",
    "MCPClient",
    "MCPToolAdapter",
    "synthesize_qaoa_turns",
    "export_qaoa_jsonl",
    "load_qaoa_jsonl",
    "export_sft_jsonl",
    "evaluate_qaoa_predictions",
    "load_toolset_json",
    "export_conversations_jsonl",
    "load_conversations_jsonl",
]
