"""Structured error classification — replaces brittle substring matching."""

from __future__ import annotations

from enum import StrEnum


class ErrorKind(StrEnum):
    AUTH = "auth"
    QUOTA = "quota"
    RATE_LIMIT = "rate_limit"
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    PARSE = "parse"
    TOOL = "tool"
    SKILL = "skill"
    CONFIG = "config"
    UNKNOWN = "unknown"


_KIND_MESSAGES: dict[ErrorKind, str] = {
    ErrorKind.AUTH: "Authentication failed — check your API key with /setup",
    ErrorKind.QUOTA: "API quota exceeded — check your billing or switch provider",
    ErrorKind.RATE_LIMIT: "Rate limited — wait a moment and retry",
    ErrorKind.CONNECTION: "Connection failed — check network and provider status",
    ErrorKind.TIMEOUT: "Request timed out — the model may be overloaded",
    ErrorKind.PARSE: "Failed to parse response — the model output was malformed",
    ErrorKind.TOOL: "Tool execution failed",
    ErrorKind.SKILL: "Skill operation failed",
    ErrorKind.CONFIG: "Configuration error — run /setup to fix",
    ErrorKind.UNKNOWN: "An unexpected error occurred",
}


def classify_error(exception: Exception) -> tuple[ErrorKind, str]:
    """Classify an exception into a structured error kind and user-facing message."""
    msg = str(exception).lower()
    exc_type = type(exception).__name__

    # Authentication
    if any(kw in msg for kw in ("401", "unauthorized", "invalid api key", "incorrect api key",
                                 "authentication", "auth error", "not authorized")):
        return ErrorKind.AUTH, _KIND_MESSAGES[ErrorKind.AUTH]

    # Quota / billing
    if any(kw in msg for kw in ("429", "quota", "billing", "insufficient_quota",
                                 "exceeded your current quota", "free trial")):
        if "rate" in msg or "limit" in msg:
            return ErrorKind.RATE_LIMIT, _KIND_MESSAGES[ErrorKind.RATE_LIMIT]
        return ErrorKind.QUOTA, _KIND_MESSAGES[ErrorKind.QUOTA]

    # Rate limiting
    if any(kw in msg for kw in ("rate limit", "too many requests", "rate_limit")):
        return ErrorKind.RATE_LIMIT, _KIND_MESSAGES[ErrorKind.RATE_LIMIT]

    # Connection / network
    if any(kw in msg for kw in ("connection", "connect", "network", "dns", "refused",
                                 "unreachable", "name resolution", "getaddrinfo")):
        return ErrorKind.CONNECTION, _KIND_MESSAGES[ErrorKind.CONNECTION]

    # Timeout
    if any(kw in msg for kw in ("timeout", "timed out", "timedout")):
        return ErrorKind.TIMEOUT, _KIND_MESSAGES[ErrorKind.TIMEOUT]

    # Parse / JSON errors
    if any(kw in msg for kw in ("json", "parse", "decode", "malformed", "unexpected token")):
        return ErrorKind.PARSE, _KIND_MESSAGES[ErrorKind.PARSE]

    # Config errors
    if any(kw in msg for kw in ("config", "provider", "not configured", "no api key",
                                 "set KAGEKO_PROVIDER")):
        return ErrorKind.CONFIG, _KIND_MESSAGES[ErrorKind.CONFIG]

    # Tool errors
    if any(kw in exc_type.lower() for kw in ("tool", "toolerror")):
        return ErrorKind.TOOL, _KIND_MESSAGES[ErrorKind.TOOL]

    # Skill errors
    if any(kw in msg for kw in ("skill not found", "skill '", "skill generation")):
        return ErrorKind.SKILL, _KIND_MESSAGES[ErrorKind.SKILL]

    return ErrorKind.UNKNOWN, _KIND_MESSAGES[ErrorKind.UNKNOWN]


def format_error(exception: Exception) -> str:
    """Format an exception into a user-facing error message."""
    kind, message = classify_error(exception)
    detail = str(exception)
    if kind != ErrorKind.UNKNOWN:
        return f"[bold red]{kind.upper()}[/bold red]: {message}\n[dim]{detail}[/dim]"
    return f"[bold red]ERROR[/bold red]: {detail}"
