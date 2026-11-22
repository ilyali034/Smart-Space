"""Gateway logic against a mocked backend (no MQTT, no database)."""

import json
import uuid
from collections.abc import Callable

import httpx
import pytest

from device_gateway.backend import BackendClient, Outcome
from device_gateway.handler import GatewayHandler

PREFIX = "smart-space/devices"
DEV = uuid.uuid4()
CMD = uuid.uuid4()


class Fake:
    """Records backend calls; behaviour can be overridden per test."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []
        self.known = {str(DEV): "lamp_1"}
        self.ack_status = 200
        self.sleeps: list[float] = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content) if req.content else None
        self.calls.append((req.method, req.url.path, body))
        if req.method == "GET" and req.url.path.startswith("/api/v1/devices/"):
            did = req.url.path.rsplit("/", 1)[1]
            return httpx.Response(200, json={"slug": self.known[did]}) if did in self.known else httpx.Response(404)
        if req.url.path.endswith("/ack"):
            return httpx.Response(self.ack_status, json={})
        return httpx.Response(204)

    def paths(self, method: str | None = None) -> list[str]:
        return [p for m, p, _ in self.calls if method in (None, m)]


@pytest.fixture
def fake() -> Fake:
    return Fake()


@pytest.fixture
def make(fake: Fake) -> Callable[..., GatewayHandler]:
    def _make(clock: Callable[[], float] = lambda: 0.0, heartbeat: float = 10.0) -> GatewayHandler:
        async def nosleep(d: float) -> None:
            fake.sleeps.append(d)

        client = httpx.AsyncClient(transport=httpx.MockTransport(fake), base_url="http://b")
        return GatewayHandler(
            BackendClient(client, sleep=nosleep), topic_prefix=PREFIX, heartbeat_seconds=heartbeat, clock=clock
        )

    return _make


def msg(kind: str, **payload: object) -> tuple[str, bytes]:
    return f"{PREFIX}/{DEV}/{kind}", json.dumps({"device_id": str(DEV), **payload}).encode()


async def test_status_maps_to_availability_and_slug_is_cached(make, fake) -> None:
    h = make()
    await h.handle(*msg("status", online=True))
    await h.handle(*msg("status", online=False))
    assert fake.calls[0][:2] == ("GET", f"/api/v1/devices/{DEV}")
    assert [(m, b) for m, p, b in fake.calls if m == "PUT"] == [
        ("PUT", {"availability": "online"}),
        ("PUT", {"availability": "offline"}),
    ]
    assert fake.paths("GET") == [f"/api/v1/devices/{DEV}"]  # resolved once


async def test_status_accepts_availability_string(make, fake) -> None:
    await make().handle(*msg("status", availability="offline"))
    assert ("PUT", "/api/v1/devices/lamp_1/availability", {"availability": "offline"}) in fake.calls


async def test_unknown_device_is_negative_cached(make, fake) -> None:
    fake.known.clear()
    now = [0.0]
    h = make(clock=lambda: now[0])
    await h.handle(*msg("status", online=True))
    await h.handle(*msg("telemetry", readings={"power": True}))
    assert fake.paths("GET") == [f"/api/v1/devices/{DEV}"]  # second message did not ask again
    assert fake.paths("PUT") == []
    now[0] = 31.0  # negative cache expired -> asks again (device may have been registered meanwhile)
    fake.known[str(DEV)] = "lamp_1"
    await h.handle(*msg("status", online=True))
    assert len(fake.paths("GET")) == 2 and len(fake.paths("PUT")) == 1


async def test_telemetry_sends_changes_and_throttles_unchanged(make, fake) -> None:
    now = [0.0]
    h = make(clock=lambda: now[0], heartbeat=10.0)
    await h.handle(*msg("telemetry", readings={"power": True, "brightness": 10}))
    await h.handle(*msg("telemetry", readings={"power": True, "brightness": 10}))  # unchanged, too soon
    assert len(fake.paths("PUT")) == 1
    await h.handle(*msg("telemetry", readings={"power": True, "brightness": 50}))  # changed -> immediately
    assert len(fake.paths("PUT")) == 2
    now[0] = 11.0
    await h.handle(*msg("telemetry", readings={"power": True, "brightness": 50}))  # heartbeat
    assert len(fake.paths("PUT")) == 3
    assert fake.calls[-1][2] == {"state": {"power": True, "brightness": 50}}


async def test_offline_resets_throttle(make, fake) -> None:
    h = make()
    await h.handle(*msg("telemetry", readings={"power": True}))
    await h.handle(*msg("status", online=False))
    await h.handle(*msg("telemetry", readings={"power": True}))  # same data after a comeback must go through
    assert len([p for p in fake.paths("PUT") if p.endswith("/state")]) == 2


async def test_ack_is_forwarded_once(make, fake) -> None:
    h = make()
    await h.handle(*msg("ack", command_id=str(CMD), ok=True))
    await h.handle(*msg("ack", command_id=str(CMD), ok=True))  # QoS1 duplicate
    acks = [c for c in fake.calls if c[1].endswith("/ack")]
    assert acks == [("POST", f"/api/v1/commands/{CMD}/ack", {"ok": True})]


async def test_ack_failure_is_forwarded_as_ok_false(make, fake) -> None:
    await make().handle(*msg("ack", command_id=str(CMD), ok=False))
    assert fake.calls[-1][2] == {"ok": False}


async def test_ack_conflict_and_unknown_are_final_not_retried(make, fake) -> None:
    for status in (409, 404):
        fake.calls.clear()
        fake.ack_status = status
        h = make()
        await h.handle(*msg("ack", command_id=str(CMD), ok=True))
        assert len([c for c in fake.calls if c[1].endswith("/ack")]) == 1
        await h.handle(*msg("ack", command_id=str(CMD), ok=True))
        assert len([c for c in fake.calls if c[1].endswith("/ack")]) == 1  # remembered


async def test_ack_retries_on_5xx_then_can_be_redelivered(make, fake) -> None:
    fake.ack_status = 503
    h = make()
    await h.handle(*msg("ack", command_id=str(CMD), ok=True))
    assert len([c for c in fake.calls if c[1].endswith("/ack")]) == 3  # 3 attempts
    assert fake.sleeps == [0.5, 1.0]  # exponential backoff, no real sleeping in tests
    fake.ack_status = 200
    await h.handle(*msg("ack", command_id=str(CMD), ok=True))  # not remembered -> goes through
    assert len([c for c in fake.calls if c[1].endswith("/ack")]) == 4


@pytest.mark.parametrize(
    "topic,payload",
    [
        (f"{PREFIX}/{DEV}/telemetry", b"not json"),
        (f"{PREFIX}/{DEV}/telemetry", b"[1,2]"),
        (f"{PREFIX}/{DEV}/telemetry", b"\xff\xfe"),
        (f"{PREFIX}/{DEV}/commands", b"{}"),  # not a gateway topic
        (f"{PREFIX}/not-a-uuid/status", b"{}"),
        (f"other/{DEV}/status", b"{}"),
        (f"{PREFIX}/{DEV}/status/extra", b"{}"),
    ],
)
async def test_garbage_is_dropped_silently(make, fake, topic, payload) -> None:
    await make().handle(topic, payload)
    assert fake.calls == []


async def test_spoofed_device_id_in_payload_is_dropped(make, fake) -> None:
    other = uuid.uuid4()
    await make().handle(f"{PREFIX}/{DEV}/telemetry", json.dumps({"device_id": str(other), "readings": {"a": 1}}).encode())
    assert fake.calls == []


async def test_bad_payloads_do_not_call_backend(make, fake) -> None:
    h = make()
    await h.handle(*msg("telemetry", readings={}))
    await h.handle(*msg("telemetry", readings="x"))
    await h.handle(*msg("status", online="yes"))
    await h.handle(*msg("ack", command_id="nope", ok=True))
    await h.handle(*msg("ack", command_id=str(CMD), ok="true"))
    assert [c for c in fake.calls if c[0] != "GET"] == []


async def test_backend_outcomes_mapping() -> None:
    def resp(code: int) -> BackendClient:
        async def nosleep(d: float) -> None: ...

        t = httpx.MockTransport(lambda r: httpx.Response(code, json={}))
        return BackendClient(httpx.AsyncClient(transport=t, base_url="http://b"), sleep=nosleep)

    assert await resp(204).report_availability("x", True) is Outcome.OK
    assert await resp(404).report_availability("x", True) is Outcome.NOT_FOUND
    assert await resp(409).ack(CMD, True) is Outcome.CONFLICT
    assert await resp(403).report_state("x", {"a": 1}) is Outcome.REJECTED
    assert await resp(500).report_state("x", {"a": 1}) is Outcome.UNAVAILABLE


async def test_network_error_is_unavailable_and_handler_survives(make, fake) -> None:
    def boom(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=req)

    async def nosleep(d: float) -> None: ...

    client = httpx.AsyncClient(transport=httpx.MockTransport(boom), base_url="http://b")
    h = GatewayHandler(BackendClient(client, sleep=nosleep), topic_prefix=PREFIX)
    await h.handle(*msg("status", online=True))  # must not raise
