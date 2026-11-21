from datetime import datetime, timedelta
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
    async def history(self, device_id: UUID, limit: int, offset: int) -> Sequence[CommandEntity]: ...
    async def count_by_status(self, device_id: UUID, status: CommandStatus) -> int: ...
    async def filter_by_date_range(self, device_id: UUID, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def filter_by_action(self, device_id: UUID, action: str) -> Sequence[CommandEntity]: ...
    async def filter_by_status(self, device_id: UUID, status: CommandStatus) -> Sequence[CommandEntity]: ...
    async def paginate(self, device_id: UUID, page: int, page_size: int) -> Sequence[CommandEntity]: ...
    async def total_count(self, device_id: UUID) -> int: ...
    async def find_conflicts(self, device_id: UUID, command_id: UUID) -> Sequence[CommandEntity]: ...
    async def find_by_device_id(self, device_id: UUID) -> Sequence[CommandEntity]: ...
    async def find_by_status(self, status: CommandStatus) -> Sequence[CommandEntity]: ...
    async def find_by_action(self, action: str) -> Sequence[CommandEntity]: ...
    async def find_by_date_range(self, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_recent(self, device_id: UUID, minutes: int) -> Sequence[CommandEntity]: ...
    async def find_pending(self) -> Sequence[CommandEntity]: ...
    async def find_approved(self) -> Sequence[CommandEntity]: ...
    async def find_rejected(self) -> Sequence[CommandEntity]: ...
    async def find_dispatched(self) -> Sequence[CommandEntity]: ...
    async def find_by_command_ids(self, command_ids: Sequence[UUID]) -> Sequence[CommandEntity]: ...
    async def find_by_device_ids(self, device_ids: Sequence[UUID]) -> Sequence[CommandEntity]: ...
    async def find_by_statuses(self, statuses: Sequence[CommandStatus]) -> Sequence[CommandEntity]: ...
    async def find_by_actions(self, actions: Sequence[str]) -> Sequence[CommandEntity]: ...
    async def find_by_date_ranges(self, date_ranges: Sequence[tuple[datetime, datetime]]) -> Sequence[CommandEntity]: ...
    async def find_recent_by_device_id(self, device_id: UUID, hours: int) -> Sequence[CommandEntity]: ...
    async def find_awaiting_confirmation(self) -> Sequence[CommandEntity]: ...
    async def find_approved_commands(self) -> Sequence[CommandEntity]: ...
    async def find_rejected_commands(self) -> Sequence[CommandEntity]: ...
    async def find_dispatched_commands(self) -> Sequence[CommandEntity]: ...
    async def find_by_command_id_and_status(self, command_id: UUID, status: CommandStatus) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_status(self, device_id: UUID, status: CommandStatus) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_action(self, device_id: UUID, action: str) -> Sequence[CommandEntity]: ...
    async def find_by_command_id_and_action(self, command_id: UUID, action: str) -> Sequence[CommandEntity]: ...
    async def find_by_command_id_and_date_range(self, command_id: UUID, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_date_range(self, device_id: UUID, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_status_and_date_range(self, status: CommandStatus, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_action_and_date_range(self, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_command_id(self, device_id: UUID, command_id: UUID) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_command_ids(self, device_id: UUID, command_ids: Sequence[UUID]) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_statuses(self, device_id: UUID, statuses: Sequence[CommandStatus]) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_actions(self, device_id: UUID, actions: Sequence[str]) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_date_ranges(self, device_id: UUID, date_ranges: Sequence[tuple[datetime, datetime]]) -> Sequence[CommandEntity]: ...
    async def find_recent_by_device_ids(self, device_ids: Sequence[UUID], hours: int) -> Sequence[CommandEntity]: ...
    async def find_awaiting_confirmation_by_device_id(self, device_id: UUID) -> Sequence[CommandEntity]: ...
    async def find_approved_by_device_id(self, device_id: UUID) -> Sequence[CommandEntity]: ...
    async def find_rejected_by_device_id(self, device_id: UUID) -> Sequence[CommandEntity]: ...
    async def find_dispatched_by_device_id(self, device_id: UUID) -> Sequence[CommandEntity]: ...
    async def find_by_command_id_and_statuses(self, command_id: UUID, statuses: Sequence[CommandStatus]) -> Sequence[CommandEntity]: ...
    async def find_by_command_id_and_actions(self, command_id: UUID, actions: Sequence[str]) -> Sequence[CommandEntity]: ...
    async def find_by_command_id_and_date_ranges(self, command_id: UUID, date_ranges: Sequence[tuple[datetime, datetime]]) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_status_and_date_range(self, device_id: UUID, status: CommandStatus, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_action_and_date_range(self, device_id: UUID, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_command_id_and_action_and_date_range(self, command_id: UUID, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_command_id(self, device_id: UUID, command_id: UUID) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_command_ids(self, device_id: UUID, command_ids: Sequence[UUID]) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_statuses(self, device_id: UUID, statuses: Sequence[CommandStatus]) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_actions(self, device_id: UUID, actions: Sequence[str]) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_date_ranges(self, device_id: UUID, date_ranges: Sequence[tuple[datetime, datetime]]) -> Sequence[CommandEntity]: ...
    async def find_recent_by_device_ids(self, device_ids: Sequence[UUID], hours: int) -> Sequence[CommandEntity]: ...
    async def find_awaiting_confirmation_by_device_id(self, device_id: UUID) -> Sequence[CommandEntity]: ...
    async def find_approved_by_device_id(self, device_id: UUID) -> Sequence[CommandEntity]: ...
    async def find_rejected_by_device_id(self, device_id: UUID) -> Sequence[CommandEntity]: ...
    async def find_dispatched_by_device_id(self, device_id: UUID) -> Sequence[CommandEntity]: ...
    async def find_by_command_id_and_statuses(self, command_id: UUID, statuses: Sequence[CommandStatus]) -> Sequence[CommandEntity]: ...
    async def find_by_command_id_and_actions(self, command_id: UUID, actions: Sequence[str]) -> Sequence[CommandEntity]: ...
    async def find_by_command_id_and_date_ranges(self, command_id: UUID, date_ranges: Sequence[tuple[datetime, datetime]]) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_status_and_date_range(self, device_id: UUID, status: CommandStatus, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_action_and_date_range(self, device_id: UUID, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_command_id_and_action_and_date_range(self, command_id: UUID, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_command_id_and_status(self, device_id: UUID, command_id: UUID, status: CommandStatus) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_command_id_and_action(self, device_id: UUID, command_id: UUID, action: str) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_command_id_and_date_range(self, device_id: UUID, command_id: UUID, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_status_and_action(self, device_id: UUID, status: CommandStatus, action: str) -> Sequence[CommandEntity]: ...
    async def find_by_command_id_and_status_and_action(self, command_id: UUID, status: CommandStatus, action: str) -> Sequence[CommandEntity]: ...
    async def find_by_command_id_and_status_and_date_range(self, command_id: UUID, status: CommandStatus, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_command_id_and_action_and_date_range(self, command_id: UUID, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_status_and_date_range(self, device_id: UUID, status: CommandStatus, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_action_and_date_range(self, device_id: UUID, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_command_id_and_status_and_action(self, device_id: UUID, command_id: UUID, status: CommandStatus, action: str) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_command_id_and_status_and_date_range(self, device_id: UUID, command_id: UUID, status: CommandStatus, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def find_by_device_id_and_command_id_and_action_and_date_range(self, device_id: UUID, command_id: UUID, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]: ...
    async def list_commands(
        self,
        *,
        status: CommandStatus | None = None,
        device_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).order_by(CommandEntity.created_at.desc())
        if status is not None:
            stmt = stmt.where(CommandEntity.status == status)
        if device_id is not None:
            stmt = stmt.where(CommandEntity.device_id == device_id)
        stmt = stmt.limit(max(1, min(limit, 500))).offset(max(0, offset))
        return (await self._session.execute(stmt)).scalars().all()


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

    async def list_commands(
        self,
        *,
        status: CommandStatus | None = None,
        device_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).order_by(CommandEntity.created_at.desc())
        if status is not None:
            stmt = stmt.where(CommandEntity.status == status)
        if device_id is not None:
            stmt = stmt.where(CommandEntity.device_id == device_id)
        stmt = stmt.limit(max(1, min(limit, 500))).offset(max(0, offset))
        return (await self._session.execute(stmt)).scalars().all()

    async def system_state(self) -> SystemStateEntity:
        state = await self._session.get(SystemStateEntity, "global")
        if state is None:
            state = SystemStateEntity(id="global", emergency_stop=False)
            self._session.add(state)
            await self._session.flush()
        return state

    async def history(self, device_id: UUID, limit: int, offset: int) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.device_id == device_id).order_by(CommandEntity.created_at.desc()).limit(limit).offset(offset)
        return (await self._session.execute(stmt)).scalars().all()

    async def count_by_status(self, device_id: UUID, status: CommandStatus) -> int:
        stmt = select(func.count()).where(
            CommandEntity.device_id == device_id,
            CommandEntity.status == status,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def filter_by_date_range(self, device_id: UUID, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.created_at.between(start_date, end_date),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def filter_by_action(self, device_id: UUID, action: str) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.action == action,
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def filter_by_status(self, device_id: UUID, status: CommandStatus) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.status == status,
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def paginate(self, device_id: UUID, page: int, page_size: int) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.device_id == device_id).order_by(CommandEntity.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
        return (await self._session.execute(stmt)).scalars().all()

    async def total_count(self, device_id: UUID) -> int:
        stmt = select(func.count()).where(CommandEntity.device_id == device_id)
        return int((await self._session.execute(stmt)).scalar_one())

    async def find_conflicts(self, device_id: UUID, command_id: UUID) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.command_id != command_id,
            CommandEntity.status.in_((
                CommandStatus.PENDING,
                CommandStatus.APPROVED,
                CommandStatus.AWAITING_CONFIRMATION,
                CommandStatus.DISPATCHED,
            )),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_device_id(self, device_id: UUID) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.device_id == device_id)
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_status(self, status: CommandStatus) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.status == status)
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_action(self, action: str) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.action == action)
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_date_range(self, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.created_at.between(start_date, end_date))
        return (await self._session.execute(stmt)).scalars().all()

    async def find_recent(self, device_id: UUID, minutes: int) -> Sequence[CommandEntity]:
        since = datetime.utcnow() - timedelta(minutes=minutes)
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.created_at >= since,
        ).order_by(CommandEntity.created_at.desc())
        return (await self._session.execute(stmt)).scalars().all()

    async def find_pending(self) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.status == CommandStatus.PENDING)
        return (await self._session.execute(stmt)).scalars().all()

    async def find_approved(self) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.status == CommandStatus.APPROVED)
        return (await self._session.execute(stmt)).scalars().all()

    async def find_rejected(self) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.status == CommandStatus.REJECTED)
        return (await self._session.execute(stmt)).scalars().all()

    async def find_dispatched(self) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.status == CommandStatus.DISPATCHED)
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_command_ids(self, command_ids: Sequence[UUID]) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.command_id.in_(command_ids))
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_device_ids(self, device_ids: Sequence[UUID]) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.device_id.in_(device_ids))
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_statuses(self, statuses: Sequence[CommandStatus]) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.status.in_(statuses))
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_actions(self, actions: Sequence[str]) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(CommandEntity.action.in_(actions))
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_date_ranges(self, date_ranges: Sequence[tuple[datetime, datetime]]) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.created_at.between(date_ranges[0][0], date_ranges[0][1]),
        )
        for start_date, end_date in date_ranges[1:]:
            stmt = stmt.or_(CommandEntity.created_at.between(start_date, end_date))
        return (await self._session.execute(stmt)).scalars().all()

    async def find_recent_by_device_id(self, device_id: UUID, hours: int) -> Sequence[CommandEntity]:
        since = datetime.utcnow() - timedelta(hours=hours)
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.created_at >= since,
        ).order_by(CommandEntity.created_at.desc())
        return (await self._session.execute(stmt)).scalars().all()

    async def find_awaiting_confirmation_by_device_id(self, device_id: UUID) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.status == CommandStatus.AWAITING_CONFIRMATION,
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_approved_by_device_id(self, device_id: UUID) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.status == CommandStatus.APPROVED,
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_rejected_by_device_id(self, device_id: UUID) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.status == CommandStatus.REJECTED,
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_dispatched_by_device_id(self, device_id: UUID) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.status == CommandStatus.DISPATCHED,
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_command_id_and_statuses(self, command_id: UUID, statuses: Sequence[CommandStatus]) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.command_id == command_id,
            CommandEntity.status.in_(statuses),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_command_id_and_actions(self, command_id: UUID, actions: Sequence[str]) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.command_id == command_id,
            CommandEntity.action.in_(actions),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_command_id_and_date_ranges(self, command_id: UUID, date_ranges: Sequence[tuple[datetime, datetime]]) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.command_id == command_id,
            CommandEntity.created_at.between(date_ranges[0][0], date_ranges[0][1]),
        )
        for start_date, end_date in date_ranges[1:]:
            stmt = stmt.or_(CommandEntity.created_at.between(start_date, end_date))
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_device_id_and_status_and_date_range(self, device_id: UUID, status: CommandStatus, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.status == status,
            CommandEntity.created_at.between(start_date, end_date),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_device_id_and_action_and_date_range(self, device_id: UUID, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.action == action,
            CommandEntity.created_at.between(start_date, end_date),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_command_id_and_action_and_date_range(self, command_id: UUID, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.command_id == command_id,
            CommandEntity.action == action,
            CommandEntity.created_at.between(start_date, end_date),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_device_id_and_command_id_and_status(self, device_id: UUID, command_id: UUID, status: CommandStatus) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.command_id == command_id,
            CommandEntity.status == status,
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_device_id_and_command_id_and_action(self, device_id: UUID, command_id: UUID, action: str) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.command_id == command_id,
            CommandEntity.action == action,
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_device_id_and_command_id_and_date_range(self, device_id: UUID, command_id: UUID, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.command_id == command_id,
            CommandEntity.created_at.between(start_date, end_date),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_device_id_and_status_and_action(self, device_id: UUID, status: CommandStatus, action: str) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.status == status,
            CommandEntity.action == action,
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_command_id_and_status_and_action(self, command_id: UUID, status: CommandStatus, action: str) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.command_id == command_id,
            CommandEntity.status == status,
            CommandEntity.action == action,
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_command_id_and_status_and_date_range(self, command_id: UUID, status: CommandStatus, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.command_id == command_id,
            CommandEntity.status == status,
            CommandEntity.created_at.between(start_date, end_date),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_command_id_and_action_and_date_range(self, command_id: UUID, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.command_id == command_id,
            CommandEntity.action == action,
            CommandEntity.created_at.between(start_date, end_date),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_device_id_and_status_and_date_range(self, device_id: UUID, status: CommandStatus, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.status == status,
            CommandEntity.created_at.between(start_date, end_date),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_device_id_and_action_and_date_range(self, device_id: UUID, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.action == action,
            CommandEntity.created_at.between(start_date, end_date),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_device_id_and_command_id_and_status_and_action(self, device_id: UUID, command_id: UUID, status: CommandStatus, action: str) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.command_id == command_id,
            CommandEntity.status == status,
            CommandEntity.action == action,
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_device_id_and_command_id_and_status_and_date_range(self, device_id: UUID, command_id: UUID, status: CommandStatus, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.command_id == command_id,
            CommandEntity.status == status,
            CommandEntity.created_at.between(start_date, end_date),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_device_id_and_command_id_and_action_and_date_range(self, device_id: UUID, command_id: UUID, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.command_id == command_id,
            CommandEntity.action == action,
            CommandEntity.created_at.between(start_date, end_date),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_command_id_and_status_and_action_and_date_range(self, command_id: UUID, status: CommandStatus, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.command_id == command_id,
            CommandEntity.status == status,
            CommandEntity.action == action,
            CommandEntity.created_at.between(start_date, end_date),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_device_id_and_status_and_action_and_date_range(self, device_id: UUID, status: CommandStatus, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.device_id == device_id,
            CommandEntity.status == status,
            CommandEntity.action == action,
            CommandEntity.created_at.between(start_date, end_date),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def find_by_command_id_and_device_id_and_status_and_action_and_date_range(self, command_id: UUID, device_id: UUID, status: CommandStatus, action: str, start_date: datetime, end_date: datetime) -> Sequence[CommandEntity]:
        stmt = select(CommandEntity).where(
            CommandEntity.command_id == command_id,
            CommandEntity.device_id == device_id,
            CommandEntity.status == status,
            CommandEntity.action == action,
            CommandEntity.created_at.between(start_date, end_date),
        )
        return (await self._session.execute(stmt)).scalars().all()
