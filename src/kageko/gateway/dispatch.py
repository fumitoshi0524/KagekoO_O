from __future__ import annotations

from typing import Any


class MessageDispatch:
    """Routes messages to the agent engine and back to the platform."""

    def __init__(self, agent: Any):
        self.agent = agent

    async def handle(self, platform: str, message: Any) -> str:
        result = await self.agent.run(message.text)
        return result.answer
