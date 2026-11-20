import logging
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..entities.device_entity import DeviceEntity

log = logging.getLogger(__name__)


class DeviceRepositoryError(Exception):
    pass


class DeviceAlreadyExists(DeviceRepositoryError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"device with slug '{slug}' already exists")
        self.slug = slug


class DeviceRepository(Protocol):
    async def get(self, device_id: UUID) -> DeviceEntity | None: ...
    async def get_by_slug(self, slug: str) -> DeviceEntity | None: ...
    async def list(
        self,
        *,
        room_id: UUID | None = None,
        type_: str | None = None,
        availability: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[DeviceEntity]: ...
    async def add(self, entity: DeviceEntity) -> DeviceEntity: ...
    async def update_state(
        self, device_id: UUID, state: dict[str, object], seen_at: datetime
    ) -> bool: ...
    async def set_availability(
        self, device_id: UUID, availability: str, seen_at: datetime | None = None
    ) -> bool: ...
    async def delete(self, device_id: UUID) -> bool: ...


class SqlAlchemyDeviceRepository:
    """Does not commit. The caller (unit of work / request scope) owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, device_id: UUID) -> DeviceEntity | None:
        log.debug("Fetching device by id=%s", device_id)
        device = await self._session.get(DeviceEntity, device_id)
        if device is None:
            log.debug("Device id=%s not found", device_id)
        return device

    async def get_by_slug(self, slug: str) -> DeviceEntity | None:
        log.debug("Fetching device by slug=%r", slug)
        result = await self._session.execute(
            select(DeviceEntity).where(DeviceEntity.slug == slug)
        )
        device = result.scalar_one_or_none()
        if device is None:
            log.debug("Device slug=%r not found", slug)
        return device

    async def list(
        self,
        *,
        room_id: UUID | None = None,
        type_: str | None = None,
        availability: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[DeviceEntity]:
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        log.debug(
            "Listing devices (room_id=%s, type=%r, availability=%r, limit=%d, offset=%d)",
            room_id,
            type_,
            availability,
            limit,
            offset,
        )
        stmt = select(DeviceEntity).order_by(DeviceEntity.slug).limit(limit).offset(offset)
        if room_id is not None:
            stmt = stmt.where(DeviceEntity.room_id == room_id)
        if type_ is not None:
            stmt = stmt.where(DeviceEntity.type == type_)
        if availability is not None:
            stmt = stmt.where(DeviceEntity.availability == availability)

        result = await self._session.execute(stmt)
        devices = result.scalars().all()
        log.debug("Found %d devices", len(devices))
        return devices

    async def add(self, entity: DeviceEntity) -> DeviceEntity:
        log.debug("Adding device slug=%r (id=%s)", entity.slug, entity.id)
        self._session.add(entity)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            if "slug" in str(exc.orig):
                log.warning("Conflict when adding device: slug=%r already exists", entity.slug)
                raise DeviceAlreadyExists(entity.slug) from exc
            log.exception("Integrity error on device insert (slug=%r)", entity.slug)
            raise DeviceRepositoryError("device insert failed") from exc
        except SQLAlchemyError as exc:
            await self._session.rollback()
            log.exception("Database error on device insert (slug=%r)", entity.slug)
            raise DeviceRepositoryError("device insert failed") from exc

        log.info("Added device id=%s slug=%r", entity.id, entity.slug)
        return entity

    async def update_state(
        self, device_id: UUID, state: dict[str, object], seen_at: datetime
    ) -> bool:
        log.debug("Updating state for device id=%s (seen_at=%s)", device_id, seen_at.isoformat())
        result = await self._session.execute(
            update(DeviceEntity)
            .where(DeviceEntity.id == device_id)
            .values(state=state, last_seen_at=seen_at)
        )
        updated = result.rowcount > 0
        if not updated:
            log.warning("Failed to update state: device id=%s not found", device_id)
        return updated

    async def set_availability(
        self, device_id: UUID, availability: str, seen_at: datetime | None = None
    ) -> bool:
        values: dict[str, object] = {"availability": availability}
        if seen_at is not None:
            values["last_seen_at"] = seen_at

        result = await self._session.execute(
            update(DeviceEntity).where(DeviceEntity.id == device_id).values(**values)
        )
        updated = result.rowcount > 0
        if updated:
            log.info("Set availability=%r for device id=%s", availability, device_id)
        else:
            log.warning("Failed to set availability=%r: device id=%s not found", availability, device_id)
        return updated

    async def delete(self, device_id: UUID) -> bool:
        result = await self._session.execute(
            delete(DeviceEntity).where(DeviceEntity.id == device_id)
        )
        deleted = result.rowcount > 0
        if deleted:
            log.info("Deleted device id=%s", device_id)
        else:
            log.warning("Failed to delete: device id=%s not found", device_id)
        return deleted
