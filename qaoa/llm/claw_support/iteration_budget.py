"""Shared iteration budget (reference ``IterationBudget`` semantics, localized)."""

from __future__ import annotations

import threading


class IterationBudget:
    """Thread-safe iteration counter for parent/child agent turns.

    Mirrors reference ``IterationBudget``: caps total LLM-call iterations; optional
    refund for cheap programmatic tool rounds (reserved for future use).
    """

    def __init__(self, max_total: int) -> None:
        self.max_total = max_total
        self._used = 0
        self._lock = threading.Lock()

    def consume(self) -> bool:
        with self._lock:
            if self._used >= self.max_total:
                return False
            self._used += 1
            return True

    def refund(self) -> None:
        with self._lock:
            if self._used > 0:
                self._used -= 1

    @property
    def used(self) -> int:
        return self._used

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, self.max_total - self._used)
