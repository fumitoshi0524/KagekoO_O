from __future__ import annotations

import logging
from typing import Any

from kageko.gateway.platforms.base import IncomingMessage, PlatformAdapter

logger = logging.getLogger(__name__)


class Gateway:
    """Single-process multi-platform message gateway."""

    def __init__(self, agent: Any):
        self.agent = agent
        self.adapters: dict[str, PlatformAdapter] = {}

    def register(self, name: str, adapter: PlatformAdapter) -> None:
        self.adapters[name] = adapter

    async def start(self, platforms: list[str] | None = None) -> None:
        names = platforms or list(self.adapters.keys())
        for name in names:
            if name in self.adapters:
                await self.adapters[name].start(self.dispatch)
                logger.info("Started adapter: %s", name)

    async def dispatch(self, platform: str, message: IncomingMessage) -> None:
        logger.debug("Received message from %s/%s: %s", platform, message.chat_id, message.text[:50])
        result = await self.agent.run(message.text)
        if platform in self.adapters:
            await self.adapters[platform].send(message.chat_id, result.answer)

    async def stop(self) -> None:
        for name, adapter in self.adapters.items():
            await adapter.stop()
            logger.info("Stopped adapter: %s", name)
