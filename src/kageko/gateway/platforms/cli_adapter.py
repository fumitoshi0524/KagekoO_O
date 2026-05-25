from __future__ import annotations

from kageko.gateway.platforms.base import PlatformAdapter, IncomingMessage, MessageHandler


class CLIAdapter(PlatformAdapter):
    """Local CLI adapter for interactive use."""

    def __init__(self, name: str = "cli"):
        super().__init__(name)
        self._handler: MessageHandler | None = None

    async def start(self, on_message: MessageHandler) -> None:
        self._handler = on_message

    async def send(self, chat_id: str, text: str) -> None:
        pass

    async def handle_input(self, text: str) -> None:
        """Called by the CLI loop to inject a message into the gateway."""
        if self._handler:
            msg = IncomingMessage(chat_id="local", text=text)
            await self._handler(self.name, msg)
