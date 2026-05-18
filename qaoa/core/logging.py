"""Logging configuration for Kageko.

This module provides structured logging with context support.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def setup_logging(
    level: str = "INFO",
    debug: bool = False,
    json_output: bool = False,
) -> None:
    """Set up structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        debug: Enable debug mode with more verbose output
        json_output: Use JSON format for logs (default: text)
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )

    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure structlog
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        # JSON output for production
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Console output for development
        if debug:
            processors.append(structlog.dev.ConsoleRenderer(colors=True))
        else:
            processors.append(structlog.processors.LogfmtRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set log level for standard logging
    logging.getLogger().setLevel(log_level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a logger instance.

    Args:
        name: Logger name (optional)

    Returns:
        Logger instance
    """
    return structlog.get_logger(name)
