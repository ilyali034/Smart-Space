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
