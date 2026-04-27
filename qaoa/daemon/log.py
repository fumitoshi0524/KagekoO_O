"""Structured logging for the daemon."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any


class StructuredLogger:
    """JSON-line logger to stderr."""

    def __init__(self, *, verbose: bool = False) -> None:
        self.verbose = verbose

    def _emit(self, level: str, message: str, meta: dict[str, Any] | None = None) -> None:
        if level == "debug" and not self.verbose:
            return
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "message": message,
        }
        if meta:
            record["meta"] = meta
        sys.stderr.write(json.dumps(record, ensure_ascii=False) + "\n")
        sys.stderr.flush()

    def info(self, message: str, **meta: Any) -> None:
        self._emit("info", message, meta if meta else None)

    def debug(self, message: str, **meta: Any) -> None:
        self._emit("debug", message, meta if meta else None)

    def warning(self, message: str, **meta: Any) -> None:
        self._emit("warning", message, meta if meta else None)

    def error(self, message: str, **meta: Any) -> None:
        self._emit("error", message, meta if meta else None)
