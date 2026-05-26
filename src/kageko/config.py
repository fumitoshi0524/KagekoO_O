# src/kageko/config.py
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib


@dataclass
class AgentConfig:
    model: str = "gpt-4o"
    mode: str = "tool-use"
    max_turns: int = 20
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    context_window_size: int = 8000
    temperature: float = 0.7
    system_prompt: str = ""


@dataclass
class SecurityConfig:
    mode: str = "interactive"
    sandbox: bool = False


@dataclass
class DatabaseConfig:
    path: str = "~/.kageko/kageko.db"


@dataclass
class LoggingConfig:
    level: str = "INFO"


@dataclass
class KagekoConfig:
    agent: AgentConfig = field(default_factory=AgentConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _load_dotenv() -> None:
    """Load .env files in priority order: user-level, then project-level."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return  # python-dotenv not installed, skip silently

    user_env = Path.home() / ".kageko" / ".env"
    if user_env.exists():
        load_dotenv(str(user_env), override=True)

    project_env = Path.cwd() / ".env"
    if project_env.exists():
        load_dotenv(str(project_env), override=False)


def load_config(path: str | None = None) -> KagekoConfig:
    _load_dotenv()
    config = KagekoConfig()
    if path and Path(path).exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)
        config = _parse_config(data)

    # Env var overrides (env wins over TOML)
    api_key = os.environ.get("KAGEKO_API_KEY")
    if api_key:
        config.agent.api_key = api_key
    model = os.environ.get("KAGEKO_MODEL")
    if model:
        config.agent.model = model
    base_url = os.environ.get("KAGEKO_BASE_URL")
    if base_url:
        config.agent.base_url = base_url

    return config


def _parse_config(data: dict) -> KagekoConfig:
    config = KagekoConfig()

    if "agent" in data:
        a = data["agent"]
        config.agent = AgentConfig(
            model=a.get("model", "gpt-4o"),
            mode=a.get("mode", "tool-use"),
            max_turns=a.get("max_turns", 20),
            api_key=a.get("api_key", ""),
            base_url=a.get("base_url", "https://api.openai.com/v1"),
            context_window_size=a.get("context_window_size", 8000),
            temperature=a.get("temperature", 0.7),
            system_prompt=a.get("system_prompt", ""),
        )

    if "security" in data:
        s = data["security"]
        config.security = SecurityConfig(
            mode=s.get("mode", "interactive"),
            sandbox=s.get("sandbox", False),
        )

    if "database" in data:
        d = data["database"]
        config.database = DatabaseConfig(path=d.get("path", "~/.kageko/kageko.db"))

    if "logging" in data:
        lg = data["logging"]
        config.logging = LoggingConfig(level=lg.get("level", "INFO"))

    return config
