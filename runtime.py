"""Compatibility wrapper for QAOA runtime API."""

from qaoa.runtime import KagekoRuntime, create_runtime

__all__: list[str] = ["KagekoRuntime", "create_runtime"]
