import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from backend_engine.modules.audit.entity import AuditLogEntity  # noqa: F401
from backend_engine.modules.devices.entity import DeviceEntity  # noqa: F401
from backend_engine.modules.devices.service import DeviceService
from backend_engine.modules.devices.uow import DevicesUnitOfWork
from backend_engine.shared.auth.principal import Principal, Role
from backend_engine.shared.auth.tokens import ApiTokenEntity  # noqa: F401
from backend_engine.shared.config import Settings
from backend_engine.shared.events.base import Event
from backend_engine.shared.events.bus import EventBus
from backend_engine.shared.storage.database import Base, create_engine, create_session_factory

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if TEST_DB_URL:
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL is not set (real PostgreSQL required)")
    for item in items:
        if "db" in item.fixturenames:
            item.add_marker(skip)


@pytest.fixture
def settings() -> Settings:
    assert TEST_DB_URL
    return Settings(database_url=TEST_DB_URL)


@pytest.fixture
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    eng = create_engine(settings)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.execute(text("TRUNCATE device, audit_log, api_token"))
    await eng.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)


class RecordingBus(EventBus):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[Event] = []

    async def publish(self, event: Event) -> None:
        self.events.append(event)


class BrokenBus(EventBus):
    async def publish(self, event: Event) -> None:
        raise RuntimeError("bus down")


@pytest.fixture
def bus() -> RecordingBus:
    return RecordingBus()


@pytest.fixture
def service(db: async_sessionmaker[AsyncSession], bus: RecordingBus) -> DeviceService:
    return DeviceService(lambda: DevicesUnitOfWork(db, bus))


@pytest.fixture
def admin() -> Principal:
    return Principal(id="admin-1", role=Role.ADMIN)


@pytest.fixture
def viewer() -> Principal:
    return Principal(id="viewer-1", role=Role.VIEWER)


@pytest.fixture
def gateway() -> Principal:
    return Principal(id="gw-1", role=Role.GATEWAY)
