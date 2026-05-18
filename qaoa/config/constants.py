"""Constants for Kageko configuration."""

from enum import Enum


class AgentName(str, Enum):
    """Agent type names."""

    CODER = "coder"
    TASK = "task"
    TITLE = "title"
    SUMMARIZER = "summarizer"


class ModelProvider(str, Enum):
    """LLM provider names."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    COPILOT = "copilot"
    BEDROCK = "bedrock"
    GROQ = "groq"
    AZURE = "azure"
    VERTEXAI = "vertexai"
    OPENROUTER = "openrouter"
    XAI = "xai"
    LOCAL = "local"


class MCPType(str, Enum):
    """MCP server connection types."""

    STDIO = "stdio"
    SSE = "sse"


class FinishReason(str, Enum):
    """Message finish reasons."""

    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    TOOL_USES = "tool_use"
    ERROR = "error"
    CANCELLED = "cancelled"
    PERMISSION_DENIED = "permission_denied"


class MessageRole(str, Enum):
    """Message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# Default paths for context loading
DEFAULT_CONTEXT_PATHS = [
    ".github/copilot-instructions.md",
    ".cursorrules",
    ".cursor/rules/",
    "CLAUDE.md",
    "CLAUDE.local.md",
    "clawcode.md",
    "clawcode.local.md",
    "ClawCode.md",
    "ClawCode.local.md",
    "CLAWCODE.md",
    "CLAWCODE.local.md",
    "kageko.md",
    "kageko.local.md",
    "KAGEKO.md",
    "KAGEKO.local.md",
]

# Default settings
DEFAULT_DATA_DIRECTORY = ".kageko"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_MAX_TOKENS = 4096

# Context window sizes for various models (for auto-compact calculation)
CONTEXT_WINDOWS = {
    "glm": 131072,
    "deepseek": 131072,
    "kimi": 131072,
    "moonshot": 131072,
    "qwen": 131072,
    "MiniMax": 204800,
    "doubao": 131072,
    "claude-3-5-sonnet-20241022": 200000,
    "claude-3-5-haiku-20241022": 200000,
    "claude-3-opus-20240229": 200000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4-turbo": 128000,
    "gemini-2.0-flash-exp": 1000000,
    "gemini-1.5-pro": 2000000,
}
