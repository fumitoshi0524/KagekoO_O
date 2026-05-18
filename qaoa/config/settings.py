"""Pydantic settings — ClawCode-style configuration management."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderConfig(BaseModel):
    api_key: str | None = None
    disabled: bool = False
    base_url: str | None = None
    timeout: int = 120
    models: list[str] = Field(default_factory=list)


class AgentConfig(BaseModel):
    model: str
    max_tokens: int = 8192
    reasoning_effort: str = "medium"
    temperature: float | None = None
    provider_key: str | None = None


class TuiConfig(BaseModel):
    theme: str = "onedark"
    display_mode: str = "full"
    mouse_enabled: bool = True
    save_theme_preference: bool = True


class PluginConfig(BaseModel):
    enabled: bool = True
    plugin_dirs: list[str] = Field(default_factory=list)
    disabled_plugins: list[str] = Field(default_factory=list)
    data_root_mode: str = ""
    plugins_data_root: str | None = None


class MCPServer(BaseModel):
    """MCP server configuration (Claude Code compatible)."""

    model_config = {"extra": "allow"}

    command: str = ""
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    type: str = "stdio"


class LSPConfig(BaseModel):
    """LSP server configuration stub (Claude Code compatible)."""

    model_config = {"extra": "allow"}

    command: str = ""
    args: list[str] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)


# Alias for ClawCode compat
Provider = ProviderConfig


class Settings(BaseSettings):
    """Kageko settings — loaded from env, .kageko.json, and defaults."""

    model_config = SettingsConfigDict(
        env_prefix="KAGEKO_",
        env_nested_delimiter="__",
    )

    # Provider
    provider: str = "openai"
    api_key: str | None = None
    model: str = "gpt-4.1-mini"
    base_url: str | None = None

    # Workspace
    working_directory: str = str(Path.cwd())
    skills_dir: str | None = None

    # Config
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    agents: dict[str, AgentConfig] = Field(default_factory=dict)

    # Toggles
    enable_rag: bool = False
    enable_mcp: bool = False
    debug: bool = False

    # Context paths (Claude Code compat: CLAUDE.md, etc.)
    context_paths: list[str] = Field(default_factory=list)

    # Auto-compact
    auto_compact: bool = True

    # QAOA skill quality
    skill_quality_threshold: float = 7.0
    max_regenerations: int = 3

    # Sub-configs
    tui: TuiConfig = Field(default_factory=TuiConfig)
    plugins: PluginConfig = Field(default_factory=PluginConfig)

    def get_agent_config(self, name: str) -> AgentConfig:
        return self.agents.get(name, AgentConfig(model=self.model))


def load_settings(working_directory: str | None = None) -> Settings:
    """Load settings from working directory .kageko.json + env vars."""
    kwargs: dict[str, Any] = {}
    if working_directory:
        kwargs["working_directory"] = working_directory

    settings = Settings(**kwargs)

    # Load from project .kageko.json
    if working_directory:
        project_config = Path(working_directory) / ".kageko.json"
        if project_config.exists():
            import json
            try:
                data = json.loads(project_config.read_text(encoding="utf-8"))
                for key, value in data.items():
                    if hasattr(settings, key) and value is not None:
                        setattr(settings, key, value)
            except (json.JSONDecodeError, OSError):
                pass

    # Load from user ~/.kageko/config.json
    user_config = Path.home() / ".kageko" / "config.json"
    if user_config.exists():
        import json
        try:
            data = json.loads(user_config.read_text(encoding="utf-8"))
            for key in ("provider", "api_key", "model", "base_url"):
                if key in data and getattr(settings, key, None) is None:
                    setattr(settings, key, data[key])
        except (json.JSONDecodeError, OSError):
            pass

    return settings


# Alias for ClawCode compat
get_settings = load_settings


__all__ = [
    "Settings",
    "ProviderConfig",
    "Provider",
    "AgentConfig",
    "TuiConfig",
    "PluginConfig",
    "MCPServer",
    "LSPConfig",
    "load_settings",
    "get_settings",
]
