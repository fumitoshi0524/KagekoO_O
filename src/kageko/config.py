# src/kageko/config.py
from __future__ import annotations

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


def load_config(path: str | None = None) -> KagekoConfig:
    if path and Path(path).exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return _parse_config(data)
    return KagekoConfig()


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
