"""Resolve Anthropic credentials and build AsyncAnthropic kwargs (Kageko-aligned).

Behavior matches the common coding client credential order and OAuth/Bearer
client construction (see ``ANTHROPIC_CLAUDE_COMPAT.md``).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Beta headers for enhanced features (sent with ALL auth types)
_COMMON_BETAS = [
    "interleaved-thinking-2025-05-14",
    "fine-grained-tool-streaming-2025-05-14",
]

# Additional beta headers required for OAuth/subscription auth.
_OAUTH_ONLY_BETAS = [
    "claude-code-20250219",
    "oauth-2025-04-20",
]

_CLAUDE_CODE_VERSION_FALLBACK = "2.1.74"

# OAuth client ID used by Claude Code's refresh flow (same as upstream tooling).
_OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"

_TOKEN_ENDPOINT = "https://console.anthropic.com/v1/oauth/token"

_claude_cli_version_cache: str | None = None


def detect_claude_code_version() -> str:
    """Return Claude Code CLI version for User-Agent, or a static fallback."""
    global _claude_cli_version_cache
    if _claude_cli_version_cache is not None:
        return _claude_cli_version_cache

    for cmd in ("claude", "claude-code"):
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                version = result.stdout.strip().split()[0]
                if version and version[0].isdigit():
                    _claude_cli_version_cache = version
                    return _claude_cli_version_cache
        except (OSError, subprocess.TimeoutExpired):
            pass

    _claude_cli_version_cache = _CLAUDE_CODE_VERSION_FALLBACK
    return _claude_cli_version_cache


def is_oauth_token(key: str) -> bool:
    """True if token should use Bearer/auth_token (not Console ``sk-ant-api`` key)."""
    if not key:
        return False
    if key.startswith("sk-ant-api"):
        return False
    return True


def read_claude_code_credentials() -> dict[str, Any] | None:
    """Read OAuth credentials from ``~/.claude/.credentials.json`` (kagekoAiOauth)."""
    cred_path = Path.home() / ".claude" / ".credentials.json"
    if not cred_path.exists():
        return None
    try:
        data = json.loads(cred_path.read_text(encoding="utf-8"))
        oauth_data = data.get("kagekoAiOauth")
        if oauth_data and isinstance(oauth_data, dict):
            access_token = oauth_data.get("accessToken", "")
            if access_token:
                return {
                    "accessToken": access_token,
                    "refreshToken": oauth_data.get("refreshToken", ""),
                    "expiresAt": oauth_data.get("expiresAt", 0),
                    "source": "claude_code_credentials_file",
                }
    except (json.JSONDecodeError, OSError) as e:
        logger.debug("Failed to read ~/.claude/.credentials.json: %s", e)
    return None


def is_claude_code_token_valid(creds: dict[str, Any]) -> bool:
    """Check if Claude Code credentials have a non-expired access token."""
    expires_at = creds.get("expiresAt", 0)
    if not expires_at:
        return bool(creds.get("accessToken"))
    now_ms = int(time.time() * 1000)
    return now_ms < (int(expires_at) - 60_000)


def _write_claude_code_credentials(
    access_token: str,
    refresh_token: str,
    expires_at_ms: int,
) -> None:
    cred_path = Path.home() / ".claude" / ".credentials.json"
    try:
        existing: dict[str, Any] = {}
        if cred_path.exists():
            existing = json.loads(cred_path.read_text(encoding="utf-8"))

        existing["kagekoAiOauth"] = {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "expiresAt": expires_at_ms,
        }

        cred_path.parent.mkdir(parents=True, exist_ok=True)
        cred_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        try:
            cred_path.chmod(0o600)
        except OSError:
            pass
    except OSError as e:
        logger.debug("Failed to write refreshed credentials: %s", e)


def refresh_claude_oauth_token(creds: dict[str, Any]) -> str | None:
    """Refresh OAuth access token using refresh_token; updates credentials file."""
    refresh_token = creds.get("refreshToken", "")
    if not refresh_token:
        logger.debug("No refresh token available — cannot refresh")
        return None

    data = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": _OAUTH_CLIENT_ID,
        }
    ).encode()

    ua_version = detect_claude_code_version()
    req = urllib.request.Request(
        _TOKEN_ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": f"claude-cli/{ua_version} (external, cli)",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            new_access = result.get("access_token", "")
            new_refresh = result.get("refresh_token", refresh_token)
            expires_in = int(result.get("expires_in", 3600))
            if new_access:
                new_expires_ms = int(time.time() * 1000) + (expires_in * 1000)
                _write_claude_code_credentials(new_access, new_refresh, new_expires_ms)
                logger.debug("Successfully refreshed Claude Code OAuth token")
                return new_access
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        logger.debug("Failed to refresh Claude Code token: %s", e)

    return None


def _resolve_claude_code_token_from_credentials(
    creds: dict[str, Any] | None = None,
) -> str | None:
    creds = creds or read_claude_code_credentials()
    if creds and is_claude_code_token_valid(creds):
        logger.debug("Using Claude Code credentials (auto-detected)")
        return str(creds["accessToken"])
    if creds:
        logger.debug("Claude Code credentials expired — attempting refresh")
        refreshed = refresh_claude_oauth_token(creds)
        if refreshed:
            return refreshed
        logger.debug("Token refresh failed — re-run 'claude setup-token' to reauthenticate")
    return None


def _prefer_refreshable_claude_code_token(
    env_token: str,
    creds: dict[str, Any] | None,
) -> str | None:
    """Prefer file-based refreshable token over static env OAuth when applicable."""
    if not env_token or not is_oauth_token(env_token) or not isinstance(creds, dict):
        return None
    if not creds.get("refreshToken"):
        return None

    resolved = _resolve_claude_code_token_from_credentials(creds)
    if resolved and resolved != env_token:
        logger.debug(
            "Preferring Claude Code credential file over static env OAuth token "
            "so refresh can proceed"
        )
        return resolved
    return None


def resolve_anthropic_token() -> str | None:
    """Resolve credential string from env and Claude Code files.

    Priority:
      1. ANTHROPIC_TOKEN
      2. CLAUDE_CODE_OAUTH_TOKEN
      3. ~/.claude/.credentials.json (with refresh)
      4. ANTHROPIC_API_KEY

    Does **not** read credential sources beyond those listed above (see
    ``KAAGEKO_SUPPORT_MAP.md``).
    """
    creds = read_claude_code_credentials()

    token = os.getenv("ANTHROPIC_TOKEN", "").strip()
    if token:
        preferred = _prefer_refreshable_claude_code_token(token, creds)
        if preferred:
            return preferred
        return token

    cc_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
    if cc_token:
        preferred = _prefer_refreshable_claude_code_token(cc_token, creds)
        if preferred:
            return preferred
        return cc_token

    resolved_file = _resolve_claude_code_token_from_credentials(creds)
    if resolved_file:
        return resolved_file

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        return api_key

    return None


def build_async_anthropic_client_kwargs(
    api_key_or_token: str,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Keyword arguments for ``AsyncAnthropic`` matching OAuth client behavior."""
    from httpx import Timeout

    kwargs: dict[str, Any] = {
        "max_retries": 2,
        "timeout": Timeout(timeout=900.0, connect=10.0),
    }
    if base_url:
        kwargs["base_url"] = base_url

    ua_ver = detect_claude_code_version()

    if is_oauth_token(api_key_or_token):
        all_betas = _COMMON_BETAS + _OAUTH_ONLY_BETAS
        kwargs["auth_token"] = api_key_or_token
        kwargs["default_headers"] = {
            "anthropic-beta": ",".join(all_betas),
            "user-agent": f"claude-cli/{ua_ver} (external, cli)",
            "x-app": "cli",
        }
    else:
        kwargs["api_key"] = api_key_or_token
        if _COMMON_BETAS:
            kwargs["default_headers"] = {"anthropic-beta": ",".join(_COMMON_BETAS)}

    return kwargs


__all__ = [
    "build_async_anthropic_client_kwargs",
    "detect_claude_code_version",
    "is_oauth_token",
    "read_claude_code_credentials",
    "refresh_claude_oauth_token",
    "resolve_anthropic_token",
]
