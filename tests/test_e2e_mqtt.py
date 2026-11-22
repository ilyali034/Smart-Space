"""End to end: backend (real PostgreSQL) -> real MQTT broker -> simulator -> gateway -> backend.

Needs TEST_DATABASE_URL and a reachable broker (MQTT_TEST_HOST / MQTT_TEST_PORT, default localhost:1883).
Each test uses its own random topic prefix, so a shared broker is fine."""

import asyncio
import os
import socket
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend_engine.app import create_app
from backend_engine.shared.auth.principal import Role
from backend_engine.shared.auth.tokens import ApiTokenEntity, generate_token
from backend_engine.shared.config import Settings
from device_gateway.__main__ import serve
from device_gateway.backend import BackendClient
from device_gateway.config import GatewayConfig
from device_gateway.handler import GatewayHandler
from device_simulator.config import SimConfig
from device_simulator.control import send as send_control
from device_simulator.devices import FLEETS, build_fleet
from device_simulator.provisioning import ensure_registered
from device_simulator.runner import DeviceRunner

pytestmark = pytest.mark.usefixtures("db")

MQTT_HOST = os.getenv("MQTT_TEST_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_TEST_PORT", "1883"))
SLUGS = [s.slug for s in FLEETS["living_room"]]


def _broker_up() -> bool:
    try:
        with socket.create_connection((MQTT_HOST, MQTT_PORT), timeout=1):
            return True
    except OSError:
        return False


async def eventually(check: Callable[[], Awaitable[Any]], timeout: float = 8.0, what: str = "condition") -> Any:
    loop = asyncio.get_running_loop()
    end = loop.time() + timeout
    while True:
        result = await check()
        if result:
            return result
        if loop.time() > end:
            raise AssertionError(f"timed out waiting for {what}")
        await asyncio.sleep(0.05)


class Stack:
    def __init__(self, app: Any, http: dict[str, httpx.AsyncClient], sim_cfg: SimConfig) -> None:
        self.app, self.http, self.sim_cfg = app, http, sim_cfg

    async def device(self, slug: str) -> dict[str, Any]:
        r = await self.http["admin"].get("/api/v1/devices", params={"limit": 100})
        return next(d for d in r.json() if d["slug"] == slug)

    async def submit(self, slug: str, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        r = await self.http["user"].post(
            f"/api/v1/devices/{slug}/command",
            json={"command_id": str(uuid.uuid4()), "action": action, "parameters": params or {}},
        )
        assert r.status_code == 201, r.text
        return dict(r.json())

    async def command(self, cid: str) -> dict[str, Any]:
        return dict((await self.http["user"].get(f"/api/v1/commands/{cid}")).json())

    async def wait_status(self, cid: str, status: str, timeout: float = 8.0) -> dict[str, Any]:
        async def check() -> dict[str, Any] | None:
            c = await self.command(cid)
            return c if c["status"] == status else None

        try:
            return dict(await eventually(check, timeout, f"command {status}"))
        except AssertionError:
            raise AssertionError(f"command never reached '{status}', is '{(await self.command(cid))['status']}'") from None

    async def wait_device(self, slug: str, **expected: Any) -> dict[str, Any]:
        async def check() -> dict[str, Any] | None:
            d = await self.device(slug)
            have = {**d["state"], "availability": d["availability"]}
            return d if all(have.get(k) == v for k, v in expected.items()) else None

        return dict(await eventually(check, 10.0, f"{slug} {expected}"))

    async def control(self, op: str, slug: str, **extra: Any) -> None:
        await send_control(self.sim_cfg, {"device": slug, "op": op, **extra})


async def _token(db: async_sessionmaker[AsyncSession], role: Role) -> str:
    raw, h = generate_token()
    async with db() as s, s.begin():
        s.add(ApiTokenEntity(name=role.value, token_hash=h, role=role.value))
    return raw


@pytest.fixture
async def stack(db: async_sessionmaker[AsyncSession]) -> AsyncIterator[Stack]:
    if not _broker_up():
        pytest.skip(f"no MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
    prefix = f"test/{uuid.uuid4().hex[:8]}"
    cfg = Settings(
        database_url=os.environ["TEST_DATABASE_URL"],
        mqtt_host=MQTT_HOST, mqtt_port=MQTT_PORT, mqtt_topic_prefix=prefix,
    )
    app = create_app(cfg)
    async with app.router.lifespan_context(app):
        http = {}
        for role in (Role.ADMIN, Role.USER, Role.GATEWAY):
            http[role.value] = httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://t",
                headers={"Authorization": f"Bearer {await _token(db, role)}"},
            )
        sim_cfg = SimConfig(mqtt_host=MQTT_HOST, mqtt_port=MQTT_PORT, topic_prefix=prefix, interval=0.3)
        ids = await ensure_registered(http["admin"], FLEETS["living_room"])
        devices = build_fleet(["living_room"])
        for d in devices:
            d.device_id = ids[d.slug]

        gw_cfg = GatewayConfig(mqtt_host=MQTT_HOST, mqtt_port=MQTT_PORT, topic_prefix=prefix)
        handler = GatewayHandler(BackendClient(http["gateway"]), topic_prefix=prefix, heartbeat_seconds=0.5)
        tasks = [asyncio.create_task(serve(handler, gw_cfg, identifier=f"gw-{prefix}"))]
        tasks += [asyncio.create_task(DeviceRunner(d, sim_cfg).run()) for d in devices]

        st = Stack(app, http, sim_cfg)
        try:
            for slug in SLUGS:
                await st.wait_device(slug, availability="online")
            yield st
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            for c in http.values():
                await c.aclose()


async def test_devices_come_online_and_sensors_report_state(stack: Stack) -> None:
    d = await stack.wait_device("living_temp")
    assert d["availability"] == "online" and d["last_seen_at"] is not None
    await eventually(lambda: _has(stack, "living_temp", "temperature"), what="temperature in state")
    lamp = await stack.wait_device("living_lamp", power=False, brightness=100)
    assert lamp["state"] == {"power": False, "brightness": 100}


async def _has(stack: Stack, slug: str, key: str) -> bool:
    return key in (await stack.device(slug))["state"]


async def test_light_command_round_trip(stack: Stack) -> None:
    cmd = await stack.submit("living_lamp", "turn_on")
    assert cmd["status"] in ("dispatched", "approved")  # accepted is NOT executed
    done = await stack.wait_status(cmd["command_id"], "acknowledged")
    assert done["acked_at"] is not None
    await stack.wait_device("living_lamp", power=True)

    cmd = await stack.submit("living_lamp", "set_brightness", {"brightness": 30})
    await stack.wait_status(cmd["command_id"], "acknowledged")
    await stack.wait_device("living_lamp", power=True, brightness=30)


async def test_relay_needs_human_confirmation_before_it_acts(stack: Stack) -> None:
    cmd = await stack.submit("living_relay", "turn_on")
    assert cmd["status"] == "awaiting_confirmation"
    await asyncio.sleep(1.0)
    assert (await stack.device("living_relay"))["state"]["power"] is False  # nothing happened yet

    r = await stack.http["user"].post(f"/api/v1/commands/{cmd['command_id']}/confirm")
    assert r.status_code == 200
    await stack.wait_status(cmd["command_id"], "acknowledged")
    await stack.wait_device("living_relay", power=True)


async def test_fault_device_cannot_execute_gives_failed(stack: Stack) -> None:
    await stack.control("faults", "living_lamp", faults={"fail_next": 1})
    await asyncio.sleep(0.3)
    cmd = await stack.submit("living_lamp", "turn_on")
    await stack.wait_status(cmd["command_id"], "failed")
    assert (await stack.device("living_lamp"))["state"]["power"] is False  # state unchanged
    cmd2 = await stack.submit("living_lamp", "turn_on")  # fault was one-shot
    await stack.wait_status(cmd2["command_id"], "acknowledged")


async def test_fault_slow_ack_state_changes_before_ack(stack: Stack) -> None:
    await stack.control("faults", "living_lamp", faults={"ack_delay": 1.5})
    await asyncio.sleep(0.3)
    cmd = await stack.submit("living_lamp", "turn_on")
    await stack.wait_device("living_lamp", power=True)
    assert (await stack.command(cmd["command_id"]))["status"] == "dispatched"  # still waiting for the ack
    await stack.wait_status(cmd["command_id"], "acknowledged", timeout=6.0)


async def test_fault_lost_ack_leaves_command_dispatched_until_timeout(stack: Stack) -> None:
    await stack.control("faults", "living_lamp", faults={"drop_next": 1})
    await asyncio.sleep(0.3)
    cmd = await stack.submit("living_lamp", "turn_on")
    await stack.wait_device("living_lamp", power=True)  # device did execute it
    await asyncio.sleep(1.5)
    assert (await stack.command(cmd["command_id"]))["status"] == "dispatched"  # but no ack ever came
    assert await stack.app.state.command_service.timeout_dispatched(0) == 1
    assert (await stack.command(cmd["command_id"]))["status"] == "timed_out"


async def test_duplicate_ack_is_harmless(stack: Stack) -> None:
    await stack.control("faults", "living_lamp", faults={"duplicate_ack": True})
    await asyncio.sleep(0.3)
    cmd = await stack.submit("living_lamp", "turn_on")
    first = await stack.wait_status(cmd["command_id"], "acknowledged")
    await asyncio.sleep(0.5)
    again = await stack.command(cmd["command_id"])
    assert again["status"] == "acknowledged" and again["acked_at"] == first["acked_at"]


async def test_offline_device_is_refused_by_safety_then_recovers(stack: Stack) -> None:
    await stack.control("offline", "living_lamp")
    await stack.wait_device("living_lamp", availability="offline")
    cmd = await stack.submit("living_lamp", "turn_on")
    assert cmd["status"] == "rejected" and cmd["decision_reasons"] == ["device_offline"]

    await stack.control("online", "living_lamp")
    await stack.wait_device("living_lamp", availability="online")
    cmd = await stack.submit("living_lamp", "turn_on")
    await stack.wait_status(cmd["command_id"], "acknowledged")


async def test_crash_is_detected_through_last_will_and_device_reboots(stack: Stack) -> None:
    await stack.control("crash", "living_temp")
    await stack.wait_device("living_temp", availability="offline")  # broker published the Will
    await stack.wait_device("living_temp", availability="online")  # simulated reboot reconnects
