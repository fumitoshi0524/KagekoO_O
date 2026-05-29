# src/kageko/config.py
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from kageko.tools.mcp_client import MCPServerConfig


@dataclass
class ProviderConfig:
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    api_key_env: str = ""


@dataclass
class AgentConfig:
    model: str = "gpt-4o"
    mode: str = "tool-use"
    max_turns: int = 20
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    context_window_size: int = 0  # 0 = auto-detect from model info
    temperature: float = 0.7
    system_prompt: str = ""
    provider: str = ""
    workspace_root: str = ""  # empty = auto (cwd at startup)

    def get_context_window_size(self) -> int:
        """Resolve context window size, auto-detecting from provider/model if set to 0."""
        if self.context_window_size > 0:
            return self.context_window_size
        # Try to auto-detect from provider profile
        try:
            from kageko.llm.providers import resolve_provider, get_model_info
            profile = resolve_provider(self.provider) if self.provider else None
            if profile:
                info = get_model_info(profile, self.model)
                if info and info.context_window > 0:
                    return info.context_window
        except Exception:
            pass
        return 8000  # fallback default


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
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    mcp_servers: dict[str, MCPServerConfig] = field(default_factory=dict)


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

    # Auto-discover user config if no explicit path
    if path is None:
        default_path = Path.home() / ".kageko" / "kageko.toml"
        if default_path.exists():
            path = str(default_path)

    if path and Path(path).exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)
        config = _parse_config(data)
        _resolve_providers(config)

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
            context_window_size=a.get("context_window_size", 0),
            temperature=a.get("temperature", 0.7),
            system_prompt=a.get("system_prompt", ""),
            provider=a.get("provider", ""),
            workspace_root=a.get("workspace_root", ""),
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

    if "providers" in data:
        for name, p in data["providers"].items():
            config.providers[name] = ProviderConfig(
                base_url=p.get("base_url", "https://api.openai.com/v1"),
                api_key=p.get("api_key", ""),
                api_key_env=p.get("api_key_env", ""),
            )

    if "mcp_servers" in data:
        for name, s in data["mcp_servers"].items():
            config.mcp_servers[name] = MCPServerConfig(
                name=name,
                command=s.get("command", ""),
                args=s.get("args", []),
                env=s.get("env", {}),
                url=s.get("url", ""),
                transport=s.get("transport", "stdio"),
            )

    return config


def _toml_val(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        escaped = (v
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        return f'"{escaped}"'
    return str(v)


def save_config(config: KagekoConfig, path: str | None = None) -> str:
    """Write KagekoConfig to a TOML file. Returns the path written."""
    if path is None:
        path = str(Path.home() / ".kageko" / "kageko.toml")

    lines = []

    # [agent]
    lines.append("[agent]")
    for f in ["model", "mode", "max_turns", "api_key", "base_url",
              "context_window_size", "temperature", "system_prompt", "provider"]:
        lines.append(f"{f} = {_toml_val(getattr(config.agent, f))}")
    lines.append("")

    # [security]
    lines.append("[security]")
    lines.append(f"mode = {_toml_val(config.security.mode)}")
    lines.append(f"sandbox = {_toml_val(config.security.sandbox)}")
    lines.append("")

    # [database]
    lines.append("[database]")
    lines.append(f"path = {_toml_val(config.database.path)}")
    lines.append("")

    # [logging]
    lines.append("[logging]")
    lines.append(f"level = {_toml_val(config.logging.level)}")
    lines.append("")

    # [providers.<name>]
    for name, prov in config.providers.items():
        lines.append(f"[providers.{name}]")
        lines.append(f"base_url = {_toml_val(prov.base_url)}")
        if prov.api_key is not None:
            lines.append(f"api_key = {_toml_val(prov.api_key)}")
        if prov.api_key_env is not None:
            lines.append(f"api_key_env = {_toml_val(prov.api_key_env)}")
        lines.append("")

    # [mcp_servers.<name>]
    for name, srv in config.mcp_servers.items():
        lines.append(f"[mcp_servers.{name}]")
        if srv.command is not None:
            lines.append(f"command = {_toml_val(srv.command)}")
        if srv.args is not None:
            args_str = ", ".join(_toml_val(a) for a in srv.args)
            lines.append(f"args = [{args_str}]")
        if srv.url is not None:
            lines.append(f"url = {_toml_val(srv.url)}")
        if srv.transport != "stdio":
            lines.append(f"transport = {_toml_val(srv.transport)}")
        if srv.env:
            env_pairs = ", ".join(f"{_toml_val(k)} = {_toml_val(v)}" for k, v in srv.env.items())
            lines.append(f"env = {{ {env_pairs} }}")
        lines.append("")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    return path


def _resolve_providers(config: KagekoConfig) -> None:
    if not config.providers or not config.agent.provider:
        return
    provider = config.providers.get(config.agent.provider)
    if provider is None:
        return
    # Resolve API key: env var first, then direct key, then preset key
    if config.agent.api_key is None or config.agent.api_key == "":
        if provider.api_key_env:
            config.agent.api_key = os.environ.get(provider.api_key_env, "")
        if not config.agent.api_key and provider.api_key:
            config.agent.api_key = provider.api_key
    # Resolve base_url: TOML override first
    if provider.base_url and config.agent.base_url == "https://api.openai.com/v1":
        config.agent.base_url = provider.base_url
    # Also try resolving via provider presets for any remaining defaults
    from kageko.llm.providers import resolve_provider as _resolve_provider_profile
    profile = _resolve_provider_profile(config.agent.provider, {
        "base_url": provider.base_url,
        "api_key": provider.api_key,
        "api_key_env": provider.api_key_env,
    })
    if not config.agent.api_key and profile.api_key:
        config.agent.api_key = profile.api_key
    # Apply preset base_url as fallback if still at OpenAI default
    if config.agent.base_url == "https://api.openai.com/v1" and profile.base_url:
        config.agent.base_url = profile.base_url
