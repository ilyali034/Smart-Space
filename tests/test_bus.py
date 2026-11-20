import asyncio

from backend_engine.shared.events.base import Event
from backend_engine.shared.events.bus import EventBus


class Ping(Event):
    n: int = 0


async def test_delivery() -> None:
    bus = EventBus()
    got: list[int] = []

    async def h(e: Ping) -> None:
        got.append(e.n)

    bus.subscribe(Ping, h)
    await bus.start()
    await bus.publish(Ping(n=1))
    await bus.stop()
    assert got == [1]


async def test_handler_error_is_isolated() -> None:
    bus = EventBus()
    got: list[int] = []

    async def bad(e: Ping) -> None:
        raise ValueError("boom")

    async def good(e: Ping) -> None:
        got.append(e.n)

    bus.subscribe(Ping, bad)
    bus.subscribe(Ping, good)
    await bus.start()
    await bus.publish(Ping(n=1))
    await bus.publish(Ping(n=2))
    await bus.stop()
    assert got == [1, 2]


async def test_lossy_drops_oldest() -> None:
    bus = EventBus()
    gate = asyncio.Event()
    got: list[int] = []

    async def slow(e: Ping) -> None:
        await gate.wait()
        got.append(e.n)

    bus.subscribe(Ping, slow, maxsize=2, lossy=True)
    await bus.start()
    for i in range(6):
        await bus.publish(Ping(n=i))
        await asyncio.sleep(0)
    gate.set()
    await bus.stop()
    assert got[-1] == 5
    assert len(got) < 6


def test_event_rejects_unknown_field() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Ping(correlaction_id=None)  # type: ignore[call-arg]
