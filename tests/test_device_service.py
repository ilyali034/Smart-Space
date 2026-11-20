import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend_engine.modules.audit.entity import AuditLogEntity
from backend_engine.modules.devices.dto import Availability, CreateDeviceDto, DeviceDto, DeviceType
from backend_engine.modules.devices.events import DeviceAvailabilityChanged, DeviceStateChanged
from backend_engine.modules.devices.exceptions import (
    DeviceAlreadyExists,
    DeviceDisabled,
    DeviceNotFound,
)
from backend_engine.modules.devices.service import DeviceService
from backend_engine.modules.devices.uow import DevicesUnitOfWork
from backend_engine.shared.auth.principal import Forbidden, Principal
from tests.conftest import BrokenBus, RecordingBus

pytestmark = pytest.mark.usefixtures("db")


def light(slug: str = "living_room_light") -> CreateDeviceDto:
    return CreateDeviceDto(slug=slug, name="Light", type=DeviceType.SMART_LIGHT, capabilities=["on_off"])


async def audit_count(db: async_sessionmaker[AsyncSession]) -> int:
    async with db() as s:
        return (await s.execute(select(func.count()).select_from(AuditLogEntity))).scalar_one()


async def test_create_returns_dto_and_audits(
    service: DeviceService, admin: Principal, db: async_sessionmaker[AsyncSession]
) -> None:
    dto = await service.create(admin, light())
    assert isinstance(dto, DeviceDto)
    assert dto.slug == "living_room_light"
    assert dto.enabled is True
    assert dto.availability == Availability.UNKNOWN
    assert dto.state == {}
    assert await audit_count(db) == 1
    assert (await service.get(admin, dto.id)).id == dto.id


async def test_create_forbidden_for_viewer(service: DeviceService, viewer: Principal) -> None:
    with pytest.raises(Forbidden):
        await service.create(viewer, light())


async def test_duplicate_slug_rolls_back_everything(
    service: DeviceService,
    admin: Principal,
    db: async_sessionmaker[AsyncSession],
    bus: RecordingBus,
) -> None:
    await service.create(admin, light())
    with pytest.raises(DeviceAlreadyExists):
        await service.create(admin, light())
    assert await audit_count(db) == 1  # only the first create
    assert len(await service.list_devices(admin)) == 1
    assert bus.events == []


async def test_get_not_found(service: DeviceService, admin: Principal) -> None:
    with pytest.raises(DeviceNotFound):
        await service.get(admin, uuid4())


async def test_list_filters_and_pagination(service: DeviceService, admin: Principal) -> None:
    for i in range(5):
        await service.create(admin, light(f"lamp_{i}"))
    await service.create(
        admin, CreateDeviceDto(slug="temp_1", name="T", type=DeviceType.TEMPERATURE_SENSOR)
    )
    assert len(await service.list_devices(admin)) == 6
    assert len(await service.list_devices(admin, type_="smart_light")) == 5
    page = await service.list_devices(admin, limit=2, offset=2)
    assert [d.slug for d in page] == ["lamp_2", "lamp_3"]


async def test_delete_only_admin_and_audited(
    service: DeviceService,
    admin: Principal,
    gateway: Principal,
    db: async_sessionmaker[AsyncSession],
) -> None:
    dto = await service.create(admin, light())
    with pytest.raises(Forbidden):
        await service.delete(gateway, dto.id)
    await service.delete(admin, dto.id)
    with pytest.raises(DeviceNotFound):
        await service.get(admin, dto.id)
    assert await audit_count(db) == 2
    with pytest.raises(DeviceNotFound):
        await service.delete(admin, dto.id)


async def test_report_state_first_report_emits_state_and_availability(
    service: DeviceService, admin: Principal, gateway: Principal, bus: RecordingBus
) -> None:
    await service.create(admin, light())
    await service.report_state(gateway, "living_room_light", {"on": True})
    types = {type(e) for e in bus.events}
    assert types == {DeviceStateChanged, DeviceAvailabilityChanged}
    dto = (await service.list_devices(admin))[0]
    assert dto.state == {"on": True}
    assert dto.availability == Availability.ONLINE
    assert dto.last_seen_at is not None


async def test_report_same_state_emits_nothing_but_updates_last_seen(
    service: DeviceService, admin: Principal, gateway: Principal, bus: RecordingBus
) -> None:
    await service.create(admin, light())
    await service.report_state(gateway, "living_room_light", {"on": True})
    first = (await service.list_devices(admin))[0].last_seen_at
    bus.events.clear()
    await asyncio.sleep(0.01)
    await service.report_state(gateway, "living_room_light", {"on": True})
    assert bus.events == []
    second = (await service.list_devices(admin))[0].last_seen_at
    assert first is not None and second is not None and second > first


async def test_report_state_merges_and_records_previous(
    service: DeviceService, admin: Principal, gateway: Principal, bus: RecordingBus
) -> None:
    await service.create(admin, light())
    await service.report_state(gateway, "living_room_light", {"on": True, "brightness": 50})
    bus.events.clear()
    await service.report_state(gateway, "living_room_light", {"brightness": 80})
    [ev] = bus.events
    assert isinstance(ev, DeviceStateChanged)
    assert ev.changed == {"brightness": 80}
    assert ev.previous == {"brightness": 50}
    assert (await service.list_devices(admin))[0].state == {"on": True, "brightness": 80}


async def test_report_state_correlation_id_propagates(
    service: DeviceService, admin: Principal, gateway: Principal, bus: RecordingBus
) -> None:
    await service.create(admin, light())
    cid = uuid4()
    await service.report_state(gateway, "living_room_light", {"on": True}, correlation_id=cid)
    assert bus.events and all(e.correlation_id == cid for e in bus.events)


async def test_report_state_unknown_and_forbidden(
    service: DeviceService, admin: Principal, gateway: Principal, viewer: Principal
) -> None:
    with pytest.raises(DeviceNotFound):
        await service.report_state(gateway, "nope", {"on": True})
    await service.create(admin, light())
    with pytest.raises(Forbidden):
        await service.report_state(viewer, "living_room_light", {"on": True})


async def test_report_state_disabled_device(
    service: DeviceService,
    admin: Principal,
    gateway: Principal,
    db: async_sessionmaker[AsyncSession],
) -> None:
    dto = await service.create(admin, light())
    async with db() as s, s.begin():
        from backend_engine.modules.devices.entity import DeviceEntity

        (await s.get(DeviceEntity, dto.id)).enabled = False  # type: ignore[union-attr]
    with pytest.raises(DeviceDisabled):
        await service.report_state(gateway, "living_room_light", {"on": True})


async def test_set_availability_offline_emits_once(
    service: DeviceService, admin: Principal, gateway: Principal, bus: RecordingBus
) -> None:
    await service.create(admin, light())
    await service.set_availability(gateway, "living_room_light", Availability.OFFLINE)
    await service.set_availability(gateway, "living_room_light", Availability.OFFLINE)
    evs = [e for e in bus.events if isinstance(e, DeviceAvailabilityChanged)]
    assert len(evs) == 1
    assert evs[0].previous == Availability.UNKNOWN
    assert evs[0].availability == Availability.OFFLINE


async def test_bus_failure_after_commit_keeps_data(
    db: async_sessionmaker[AsyncSession], admin: Principal, gateway: Principal
) -> None:
    broken = DeviceService(lambda: DevicesUnitOfWork(db, BrokenBus()))
    await broken.create(admin, light())
    await broken.report_state(gateway, "living_room_light", {"on": True})  # must not raise
    assert (await broken.list_devices(admin))[0].state == {"on": True}


async def test_failed_transaction_publishes_nothing(
    db: async_sessionmaker[AsyncSession], admin: Principal, bus: RecordingBus
) -> None:
    svc = DeviceService(lambda: DevicesUnitOfWork(db, bus))
    await svc.create(admin, light())
    uow = DevicesUnitOfWork(db, bus)
    with pytest.raises(RuntimeError):
        async with uow:
            uow.add_event(
                DeviceStateChanged(
                    device_id=uuid4(), slug="x", room_id=None, changed={}, previous={}
                )
            )
            raise RuntimeError("fail before commit")
    assert bus.events == []


async def test_concurrent_reports_are_consistent(
    service: DeviceService, admin: Principal, gateway: Principal
) -> None:
    await service.create(admin, light())
    await asyncio.gather(
        *(service.report_state(gateway, "living_room_light", {f"k{i}": i}) for i in range(50))
    )
    state = (await service.list_devices(admin))[0].state
    assert state == {f"k{i}": i for i in range(50)}  # no lost updates (SELECT ... FOR UPDATE)
