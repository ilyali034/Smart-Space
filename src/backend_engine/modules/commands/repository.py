from datetime import datetime
from typing import Protocol, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend_engine.modules.commands.entity import CommandEntity, CommandStatus, SystemStateEntity


class CommandRepository(Protocol):
    async def get_by_command_id(self, command_id: UUID, *, lock: bool = False) -> CommandEntity | None: ...
    async def get_by_id(self, command_id: UUID, *, lock: bool = False) -> CommandEntity | None: ...
    async def add(self, entity: CommandEntity) -> CommandEntity: ...
    async def recent_count(self, device_id: UUID, since: datetime) -> int: ...
    async def active_conflicts(self, device_id: UUID, action: str) -> Sequence[CommandEntity]: ...
    async def system_state(self) -> SystemStateEntity: ...
    async def awaiting_confirmation(self) -> Sequence[CommandEntity]: ...
    async def approved(self) -> Sequence[CommandEntity]: ...
    async def dispatched_before(self, since: datetime) -> Sequence[CommandEntity]: ...


class SqlAlchemyCommandRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_command_id(self, command_id: UUID, *, lock: bool = False) -> CommandEntity | None:
        stmt = select(CommandEntity).where(CommandEntity.command_id == command_id)
        if lock:
            stmt = stmt.with_for_update()
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, command_id: UUID, *, lock: bool = False) -> CommandEntity | None:
        return await self.get_by_command_id(command_id, lock=lock)

    async def add(self, entity: CommandEntity) -> CommandEntity:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def recent_count(self, device_id: UUID, since: datetime) -> int:
        stmt = select(func.count()).select_from(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.created_at >= since,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def active_conflicts(self, device_id: UUID, action: str) -> Sequence[CommandEntity]:
        opposite = "turn_off" if action == "turn_on" else "turn_on" if action == "turn_off" else ""
        if not opposite:
            return ()
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.action == opposite,
            CommandEntity.status.in_((
                CommandStatus.PENDING,
                CommandStatus.APPROVED,
                CommandStatus.AWAITING_CONFIRMATION,
                CommandStatus.DISPATCHED,
            )),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def awaiting_confirmation(self) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.status == CommandStatus.AWAITING_CONFIRMATION)
        return (await self._session.execute(stmt)).scalars().all()

    async def approved(self) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.status == CommandStatus.APPROVED)
        return (await self._session.execute(stmt)).scalars().all()

    async def dispatched_before(self, since: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.status == CommandStatus.DISPATCHED,
            CommandEntity.dispatched_at.is_not(None),
            CommandEntity.dispatched_at < since,
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def system_state(self) -> SystemStateEntity:
        state = await self._session.get(SystemStateEntity, "global")
        if state is None:
            state = SystemStateEntity(id="global", emergency_stop=False)
            self._session.add(state)
            await self._session.flush()
        return state
