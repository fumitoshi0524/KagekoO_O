"""AppContext — dependency injection container matching ClawCode's pattern."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config.settings import Settings, load_settings
from .core.pubsub import Broker
from .db.connection import Database
from .session.service import SessionService
from .message.service import MessageService


@dataclass(slots=True, kw_only=True)
class AppContext:
    """Central dependency injection container — created once at startup."""

    settings: Settings
    broker: Broker = field(default_factory=Broker)
    _db: Database | None = None
    _session_service: SessionService | None = None
    _message_service: MessageService | None = None

    @property
    def db(self) -> Database:
        if self._db is None:
            data_dir = Path.home() / ".kageko" / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self._db = Database(data_dir)
        return self._db

    @property
    def session_service(self) -> SessionService:
        if self._session_service is None:
            self._session_service = SessionService(self.db, self.broker)
        return self._session_service

    @property
    def message_service(self) -> MessageService:
        if self._message_service is None:
            self._message_service = MessageService(self.db, self.broker)
        return self._message_service


def create_app_context(
    *,
    working_directory: str | None = None,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> AppContext:
    """Create the application context — matches ClawCode's create_app() pattern."""
    settings = load_settings(working_directory)
    if provider:
        settings.provider = provider
    if api_key:
        settings.api_key = api_key
    if model:
        settings.model = model
    return AppContext(settings=settings)
