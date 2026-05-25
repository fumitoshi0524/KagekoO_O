from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


@dataclass
class IncomingMessage:
    chat_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


MessageHandler = Callable[[str, IncomingMessage], Awaitable[None]]


class PlatformAdapter(ABC):
    """Base class for platform adapters."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def start(self, on_message: MessageHandler) -> None:
        """Start listening for messages."""

    @abstractmethod
    async def send(self, chat_id: str, text: str) -> None:
        """Send a message to a chat."""

    async def stop(self) -> None:
        """Stop the adapter."""
