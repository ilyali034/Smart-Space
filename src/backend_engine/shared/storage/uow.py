import logging
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend_engine.shared.events.base import Event
from backend_engine.shared.events.bus import EventBus

log = logging.getLogger(__name__)


class BaseUnitOfWork:
    """One transaction. Commit on success, rollback on error.
    Events are published only after a successful commit."""

    session: AsyncSession

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], bus: EventBus) -> None:
        self._factory = session_factory
        self._bus = bus
        self._events: list[Event] = []

    def _bind(self, session: AsyncSession) -> None:
        """Hook: subclasses create repositories here."""

    def add_event(self, event: Event) -> None:
        self._events.append(event)

    async def __aenter__(self) -> Self:
        self._events = []
        self.session = self._factory()
        await self.session.begin()
        self._bind(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()
        if exc_type is None:
            await self._publish()
        else:
            self._events = []

    async def _publish(self) -> None:
        events, self._events = self._events, []
        for event in events:
            try:
                await self._bus.publish(event)
            except Exception:
                # Data is already committed. A bus failure must not fail the request.
                log.exception("event publish failed", extra={"event_type": type(event).__name__})
