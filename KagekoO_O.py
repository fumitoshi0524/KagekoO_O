"""Compatibility public API module for distribution installs."""

from core.context import ContextWindow
from core.models import AgentMode, AgentRequest, AgentResponse, ToolUse
from integrations.a2a import A2AOrchestrator, AgentRegistry, A2AMessage, MessageType
from integrations.mcp import MCPClient, MCPToolAdapter
from integrations.rag import VectorStore
from integrations.rl import RLAgent, AgentPolicy, Episode
from runtime import KagekoRuntime, create_runtime

__all__: list[str] = [
    "AgentMode",
    "AgentRequest",
    "AgentResponse",
    "ToolUse",
    "ContextWindow",
    "KagekoRuntime",
    "create_runtime",
    "VectorStore",
    "MCPClient",
    "MCPToolAdapter",
    "A2AOrchestrator",
    "AgentRegistry",
    "A2AMessage",
    "MessageType",
    "RLAgent",
    "AgentPolicy",
    "Episode",
]
