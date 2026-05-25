import pytest
from unittest.mock import AsyncMock
from kageko.gateway.server import Gateway
from kageko.gateway.platforms.base import PlatformAdapter, IncomingMessage
from kageko.gateway.platforms.cli_adapter import CLIAdapter


@pytest.fixture
def mock_engine():
    engine = AsyncMock()
    engine.run = AsyncMock(return_value=type("R", (), {"answer": "response text"})())
    return engine


@pytest.mark.asyncio
async def test_gateway_register_adapter(mock_engine):
    gw = Gateway(agent=mock_engine)
    adapter = CLIAdapter(name="cli")
    gw.register("cli", adapter)
    assert "cli" in gw.adapters


@pytest.mark.asyncio
async def test_gateway_dispatch(mock_engine):
    gw = Gateway(agent=mock_engine)
    adapter = CLIAdapter(name="cli")
    gw.register("cli", adapter)

    msg = IncomingMessage(chat_id="user1", text="hello")
    await gw.dispatch("cli", msg)
    mock_engine.run.assert_called_once_with("hello")


def test_incoming_message():
    msg = IncomingMessage(chat_id="user1", text="hello", metadata={"platform": "cli"})
    assert msg.chat_id == "user1"
    assert msg.text == "hello"
