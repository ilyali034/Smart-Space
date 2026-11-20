import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TypeVar

from .base import Event

log = logging.getLogger(__name__)

E = TypeVar("E", bound=Event)
Handler = Callable[[E], Awaitable[None]]


class _Subscription:
    def __init__(self, handler: Handler, maxsize: int, lossy: bool) -> None:
        self.handler = handler
        self.lossy = lossy
        self.queue: asyncio.Queue[Event] = asyncio.Queue(maxsize)
        self.dropped = 0
        self.task: asyncio.Task[None] | None = None


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[type[Event], list[_Subscription]] = defaultdict(list)
        self._running = False

    def subscribe(
        self,
        event_type: type[E],
        handler: Handler[E],
        *,
        maxsize: int = 1000,
        lossy: bool = False,
    ) -> None:
        sub = _Subscription(handler, maxsize, lossy)  # type: ignore[arg-type]
        self._subs[event_type].append(sub)
        if self._running:
            sub.task = asyncio.create_task(self._worker(sub))

    async def publish(self, event: Event) -> None:
        for etype, subs in self._subs.items():
            if not isinstance(event, etype):
                continue
            for sub in subs:
                if sub.lossy and sub.queue.full():
                    sub.queue.get_nowait()
                    sub.dropped += 1
                await sub.queue.put(event)

    async def start(self) -> None:
        self._running = True
        for subs in self._subs.values():
            for sub in subs:
                if sub.task is None:
                    sub.task = asyncio.create_task(self._worker(sub))

    async def stop(self, drain_timeout: float = 5.0) -> None:
        self._running = False
        subs = [s for lst in self._subs.values() for s in lst]
        try:
            await asyncio.wait_for(
                asyncio.gather(*(s.queue.join() for s in subs)), drain_timeout
            )
        except asyncio.TimeoutError:
            log.warning("event bus drain timeout")
        for s in subs:
            if s.task:
                s.task.cancel()
        await asyncio.gather(*(s.task for s in subs if s.task), return_exceptions=True)

    async def _worker(self, sub: _Subscription) -> None:
        while True:
            event = await sub.queue.get()
            try:
                await sub.handler(event)
            except Exception:
                log.exception("handler failed", extra={"event": type(event).__name__})
            finally:
                sub.queue.task_done()