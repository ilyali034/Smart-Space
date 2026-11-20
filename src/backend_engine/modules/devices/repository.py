import logging
from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend_engine.modules.devices.entity import DeviceEntity
from backend_engine.modules.devices.exceptions import DeviceAlreadyExists, DeviceRepositoryError

log = logging.getLogger(__name__)

_MAX_LIMIT = 500


class DeviceRepository(Protocol):
    async def get(self, device_id: UUID, *, lock: bool = False) -> DeviceEntity | None: ...
    async def get_by_slug(self, slug: str, *, lock: bool = False) -> DeviceEntity | None: ...
    async def list_devices(
        self,
        *,
        room_id: UUID | None = None,
        type_: str | None = None,
        availability: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[DeviceEntity]: ...
    async def add(self, entity: DeviceEntity) -> DeviceEntity: ...
    async def delete(self, device_id: UUID) -> bool: ...


class SqlAlchemyDeviceRepository:
    """Never commits and never rolls back the outer transaction.
    The unit of work owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, device_id: UUID, *, lock: bool = False) -> DeviceEntity | None:
        return await self._session.get(DeviceEntity, device_id, with_for_update=lock)

    async def get_by_slug(self, slug: str, *, lock: bool = False) -> DeviceEntity | None:
        stmt = select(DeviceEntity).where(DeviceEntity.slug == slug)
        if lock:
            stmt = stmt.with_for_update()
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_devices(
        self,
        *,
        room_id: UUID | None = None,
        type_: str | None = None,
        availability: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[DeviceEntity]:
        limit = max(1, min(limit, _MAX_LIMIT))
        offset = max(0, offset)
        stmt = select(DeviceEntity).order_by(DeviceEntity.slug).limit(limit).offset(offset)
        if room_id is not None:
            stmt = stmt.where(DeviceEntity.room_id == room_id)
        if type_ is not None:
            stmt = stmt.where(DeviceEntity.type == type_)
        if availability is not None:
            stmt = stmt.where(DeviceEntity.availability == availability)
        return (await self._session.execute(stmt)).scalars().all()

    async def add(self, entity: DeviceEntity) -> DeviceEntity:
        try:
            # Savepoint: a failed insert does not poison the outer transaction.
            async with self._session.begin_nested():
                self._session.add(entity)
                await self._session.flush()
        except IntegrityError as exc:
            if "uq_device_slug" in str(exc.orig):
                raise DeviceAlreadyExists(entity.slug) from exc
            log.exception("integrity error on device insert (slug=%r)", entity.slug)
            raise DeviceRepositoryError("device insert failed") from exc
        except SQLAlchemyError as exc:
            log.exception("database error on device insert (slug=%r)", entity.slug)
            raise DeviceRepositoryError("device insert failed") from exc
        return entity

    async def delete(self, device_id: UUID) -> bool:
        result = await self._session.execute(
            delete(DeviceEntity).where(DeviceEntity.id == device_id)
        )
        return bool(result.rowcount > 0)  # type: ignore[attr-defined]
