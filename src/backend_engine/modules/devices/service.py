import logging
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

from backend_engine.modules.devices.dto import Availability, CreateDeviceDto, DeviceDto
from backend_engine.modules.devices.entity import DeviceEntity
from backend_engine.modules.devices.events import DeviceAvailabilityChanged, DeviceStateChanged
from backend_engine.modules.devices.exceptions import DeviceDisabled, DeviceNotFound
from backend_engine.modules.devices.uow import DevicesUnitOfWork
from backend_engine.shared.auth.principal import Permission, Principal, require

log = logging.getLogger(__name__)

UowFactory = Callable[[], DevicesUnitOfWork]


class DeviceService:
    """Takes and returns DTOs. Entities live only inside a unit of work."""

    def __init__(self, uow_factory: UowFactory) -> None:
        self._uow = uow_factory

    # ---------- user-facing ----------

    async def create(
        self, actor: Principal, dto: CreateDeviceDto, *, correlation_id: UUID | None = None
    ) -> DeviceDto:
        require(actor, Permission.DEVICE_WRITE)
        entity = DeviceEntity(
            slug=dto.slug,
            name=dto.name,
            type=dto.type.value,
            room_id=dto.room_id,
            capabilities=dto.capabilities,
        )
        async with self._uow() as uow:
            await uow.devices.add(entity) 
            await uow.audit.record(
                actor=actor.id,
                action="device.create",
                target=str(entity.id),
                correlation_id=correlation_id,
                details={"slug": dto.slug, "type": dto.type.value},
            )
            return DeviceDto.model_validate(entity)

    async def get(self, actor: Principal, device_id: UUID) -> DeviceDto:
        require(actor, Permission.DEVICE_READ)
        async with self._uow() as uow:
            entity = await uow.devices.get(device_id)
            if entity is None:
                raise DeviceNotFound(device_id)
            return DeviceDto.model_validate(entity)

    async def list_devices(
        self,
        actor: Principal,
        *,
        room_id: UUID | None = None,
        type_: str | None = None,
        availability: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DeviceDto]:
        require(actor, Permission.DEVICE_READ)
        async with self._uow() as uow:
            rows = await uow.devices.list_devices(
                room_id=room_id,
                type_=type_,
                availability=availability,
                limit=limit,
                offset=offset,
            )
            return [DeviceDto.model_validate(r) for r in rows]

    async def delete(
        self, actor: Principal, device_id: UUID, *, correlation_id: UUID | None = None
    ) -> None:
        require(actor, Permission.DEVICE_DELETE)
        async with self._uow() as uow:
            entity = await uow.devices.get(device_id)
            if entity is None:
                raise DeviceNotFound(device_id)
            slug = entity.slug
            await uow.devices.delete(device_id)
            await uow.audit.record(
                actor=actor.id,
                action="device.delete",
                target=str(device_id),
                correlation_id=correlation_id,
                details={"slug": slug},
            )

    # ---------- gateway-facing (high frequency, no audit) ----------

    async def report_state(
        self,
        actor: Principal,
        slug: str,
        patch: dict[str, object],
        *,
        seen_at: datetime | None = None,
        correlation_id: UUID | None = None,
    ) -> None:
        """Merge partial state. Receiving state implies the device is online.
        Events fire only on real changes."""
        require(actor, Permission.DEVICE_REPORT)
        now = seen_at or datetime.now(timezone.utc)
        async with self._uow() as uow:
            entity = await uow.devices.get_by_slug(slug, lock=True)
            if entity is None:
                raise DeviceNotFound(slug)
            if not entity.enabled:
                raise DeviceDisabled(slug)

            changed = {k: v for k, v in patch.items() if entity.state.get(k) != v}
            entity.last_seen_at = now

            if changed:
                previous = {k: entity.state.get(k) for k in changed}
                entity.state = {**entity.state, **changed}  # new dict: JSONB change is detected
                uow.add_event(
                    DeviceStateChanged(
                        correlation_id=correlation_id,
                        device_id=entity.id,
                        slug=entity.slug,
                        room_id=entity.room_id,
                        changed=changed,
                        previous=previous,
                    )
                )
            self._apply_availability(uow, entity, Availability.ONLINE, correlation_id)

    async def set_availability(
        self,
        actor: Principal,
        slug: str,
        availability: Availability,
        *,
        seen_at: datetime | None = None,
        correlation_id: UUID | None = None,
    ) -> None:
        require(actor, Permission.DEVICE_REPORT)
        async with self._uow() as uow:
            entity = await uow.devices.get_by_slug(slug, lock=True)
            if entity is None:
                raise DeviceNotFound(slug)
            if seen_at is not None:
                entity.last_seen_at = seen_at
            self._apply_availability(uow, entity, availability, correlation_id)

    @staticmethod
    def _apply_availability(
        uow: DevicesUnitOfWork,
        entity: DeviceEntity,
        new: Availability,
        correlation_id: UUID | None,
    ) -> None:
        old = Availability(entity.availability)
        if old == new:
            return
        entity.availability = new.value
        uow.add_event(
            DeviceAvailabilityChanged(
                correlation_id=correlation_id,
                device_id=entity.id,
                slug=entity.slug,
                room_id=entity.room_id,
                availability=new,
                previous=old,
            )
        )
