from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend_engine.app import create_app
from backend_engine.shared.auth.principal import Role
from backend_engine.shared.auth.tokens import ApiTokenEntity, generate_token
from backend_engine.shared.config import Settings

pytestmark = pytest.mark.usefixtures("db")


async def _token(
    db: async_sessionmaker[AsyncSession],
    role: Role,
    *,
    expires: datetime | None = None,
    revoked: datetime | None = None,
) -> str:
    raw, h = generate_token()
    async with db() as s, s.begin():
        s.add(ApiTokenEntity(name=role.value, token_hash=h, role=role.value,
                             expires_at=expires, revoked_at=revoked))
    return raw


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as c:
        yield c


def auth(tok: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {tok}"}


BODY = {"slug": "kitchen_light", "name": "Kitchen", "type": "smart_light"}


async def test_health(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/health")
    assert r.status_code == 200


async def test_no_token_is_401(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/v1/devices")).status_code == 401
    assert (await client.get("/api/v1/devices", headers=auth("ss_bad"))).status_code == 401


async def test_expired_and_revoked_tokens_are_401(
    client: httpx.AsyncClient, db: async_sessionmaker[AsyncSession]
) -> None:
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    expired = await _token(db, Role.ADMIN, expires=past)
    revoked = await _token(db, Role.ADMIN, revoked=past)
    assert (await client.get("/api/v1/devices", headers=auth(expired))).status_code == 401
    assert (await client.get("/api/v1/devices", headers=auth(revoked))).status_code == 401


async def test_device_crud_flow(
    client: httpx.AsyncClient, db: async_sessionmaker[AsyncSession]
) -> None:
    admin = auth(await _token(db, Role.ADMIN))
    viewer = auth(await _token(db, Role.VIEWER))

    r = await client.post("/api/v1/devices", json=BODY, headers=admin)
    assert r.status_code == 201
    dev = r.json()
    assert dev["slug"] == "kitchen_light" and dev["availability"] == "unknown"

    assert (await client.post("/api/v1/devices", json=BODY, headers=admin)).status_code == 409
    assert (await client.post("/api/v1/devices", json=BODY, headers=viewer)).status_code == 403
    assert (await client.post("/api/v1/devices", json={**BODY, "slug": "A!"}, headers=admin)).status_code == 422
    assert (await client.post("/api/v1/devices", json={**BODY, "x": 1}, headers=admin)).status_code == 422

    assert (await client.get(f"/api/v1/devices/{dev['id']}", headers=viewer)).status_code == 200
    listed = await client.get("/api/v1/devices?type=smart_light", headers=viewer)
    assert [d["slug"] for d in listed.json()] == ["kitchen_light"]

    assert (await client.delete(f"/api/v1/devices/{dev['id']}", headers=viewer)).status_code == 403
    assert (await client.delete(f"/api/v1/devices/{dev['id']}", headers=admin)).status_code == 204
    assert (await client.get(f"/api/v1/devices/{dev['id']}", headers=admin)).status_code == 404


async def test_gateway_reports_availability_and_state(
    client: httpx.AsyncClient, db: async_sessionmaker[AsyncSession]
) -> None:
    admin = auth(await _token(db, Role.ADMIN))
    gw = auth(await _token(db, Role.GATEWAY))
    await client.post("/api/v1/devices", json=BODY, headers=admin)
    url = "/api/v1/devices/kitchen_light"

    assert (await client.put(f"{url}/availability", json={"availability": "online"}, headers=gw)).status_code == 204
    dev = (await client.get("/api/v1/devices", headers=admin)).json()[0]
    assert dev["availability"] == "online"

    assert (await client.put(f"{url}/availability", json={"availability": "offline"}, headers=gw)).status_code == 204
    assert (await client.get("/api/v1/devices", headers=admin)).json()[0]["availability"] == "offline"

    # state is merged, not replaced; receiving state implies online
    assert (await client.put(f"{url}/state", json={"state": {"power": True}}, headers=gw)).status_code == 204
    assert (await client.put(f"{url}/state", json={"state": {"brightness": 40}}, headers=gw)).status_code == 204
    dev = (await client.get("/api/v1/devices", headers=admin)).json()[0]
    assert dev["state"] == {"power": True, "brightness": 40}
    assert dev["availability"] == "online" and dev["last_seen_at"] is not None


async def test_report_endpoints_are_gateway_only_and_validated(
    client: httpx.AsyncClient, db: async_sessionmaker[AsyncSession]
) -> None:
    admin = auth(await _token(db, Role.ADMIN))
    gw = auth(await _token(db, Role.GATEWAY))
    await client.post("/api/v1/devices", json=BODY, headers=admin)
    url = "/api/v1/devices/kitchen_light"
    online = {"availability": "online"}

    for role in (Role.VIEWER, Role.USER):  # users must not be able to fake device state
        h = auth(await _token(db, role))
        assert (await client.put(f"{url}/availability", json=online, headers=h)).status_code == 403
        assert (await client.put(f"{url}/state", json={"state": {"a": 1}}, headers=h)).status_code == 403
    assert (await client.put(f"{url}/availability", json=online)).status_code == 401

    assert (await client.put("/api/v1/devices/nope_1/state", json={"state": {"a": 1}}, headers=gw)).status_code == 404
    assert (await client.put(f"{url}/availability", json={"availability": "bogus"}, headers=gw)).status_code == 422
    assert (await client.put(f"{url}/state", json={"state": {}}, headers=gw)).status_code == 422
    assert (await client.put(f"{url}/state", json={"state": {"a": 1}, "x": 1}, headers=gw)).status_code == 422
    too_many = {f"k{i}": i for i in range(65)}
    assert (await client.put(f"{url}/state", json={"state": too_many}, headers=gw)).status_code == 422
