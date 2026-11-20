from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select

from backend_engine.modules.audit.writer import SqlAlchemyAuditWriter
from backend_engine.modules.commands.dispatcher import CommandDispatcher
from backend_engine.modules.commands.dto import CommandDto, SubmitCommandDto
from backend_engine.modules.commands.entity import (
    CommandEntity,
    CommandStatus,
    transition_status,
)
from backend_engine.modules.commands.events import ConfirmationRequired, EmergencyStopActivated
from backend_engine.modules.commands.events import CommandResolved
from backend_engine.modules.commands.exceptions import CommandConflict, CommandNotFound, HumanConfirmationRequired
from backend_engine.modules.commands.uow import CommandsUnitOfWork
from backend_engine.modules.devices.entity import DeviceEntity
from backend_engine.modules.devices.repository import SqlAlchemyDeviceRepository
from backend_engine.modules.safety.evaluate import Verdict
from backend_engine.modules.safety.policy import DEFAULT_RULES
from backend_engine.modules.safety.evaluate import evaluate
from backend_engine.modules.safety.types import CommandRequest, CommandSource, SafetyContext
from backend_engine.shared.auth.principal import Permission, Principal, Role, require

UowFactory = Callable[[], CommandsUnitOfWork]


class CommandService:
    def __init__(self, uow_factory: UowFactory, dispatcher: CommandDispatcher, rate_limit: int = 100) -> None:
        self._uow = uow_factory
        self._dispatcher = dispatcher
        self._rate_limit = rate_limit

    async def submit(self, actor: Principal, device_slug: str, dto: SubmitCommandDto, *, correlation_id: UUID | None = None) -> CommandDto:
        require(actor, Permission.COMMAND_CREATE)
        async with self._uow() as uow:
            existing = await uow.commands.get_by_command_id(dto.command_id, lock=True)
            if existing is not None:
                existing_device = await uow.session.scalar(
                    select(DeviceEntity).where(DeviceEntity.id == existing.device_id)
                )
                same = (
                    existing_device is not None
                    and existing_device.slug == device_slug
                    and existing.action == dto.action
                    and existing.parameters == dto.parameters
                    and existing.source == dto.source.value
                )
                if not same:
                    raise CommandConflict(dto.command_id)
                return CommandDto.model_validate(existing)

            # Session-local device lookup is intentionally kept inside commands.
            device = await uow.session.scalar(select(DeviceEntity).where(DeviceEntity.slug == device_slug))
            state = await uow.commands.system_state()
            recent = await uow.commands.recent_count(device.id, datetime.now(timezone.utc) - timedelta(minutes=1)) if device else 0
            conflicts = await uow.commands.active_conflicts(device.id, dto.action) if device else ()

            ctx = SafetyContext(
                device_exists=device is not None,
                device_enabled=bool(device and device.enabled),
                device_online=bool(device and device.availability == "online"),
                device_type=str(device.type) if device else "",
                device_capabilities=tuple(device.capabilities) if device else (),
                emergency_stop=state.emergency_stop,
                recent_command_count=recent,
                rate_limit=self._rate_limit,
                active_conflicting_commands=tuple(str(x.command_id) for x in conflicts),
            )
            decision = evaluate(CommandRequest(dto.action, dto.parameters, CommandSource(dto.source)), ctx, DEFAULT_RULES)

            status = {
                Verdict.APPROVE: CommandStatus.APPROVED,
                Verdict.REJECT: CommandStatus.REJECTED,
                Verdict.CONFIRM: CommandStatus.AWAITING_CONFIRMATION,
            }[decision.verdict]
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=60) if status == CommandStatus.AWAITING_CONFIRMATION else None
            entity = CommandEntity(
                command_id=dto.command_id,
                device_id=device.id if device else UUID(int=0),
                action=dto.action,
                parameters=dto.parameters,
                status=CommandStatus.PENDING,
                source=dto.source.value,
                requested_by=actor.id,
                decision_reasons=list(decision.reasons),
                correlation_id=correlation_id,
                expires_at=expires_at,
            )
            await uow.commands.add(entity)
            transition_status(entity, status)
            await uow.audit.record(actor=actor.id, action="command.submit", target=str(dto.command_id), correlation_id=correlation_id, details={"status": status.value, "action": dto.action, "device": device_slug, "reasons": list(decision.reasons)})
            uow.add_event(CommandResolved(command_id=dto.command_id, device_id=entity.device_id, status=status, action=dto.action, reasons=decision.reasons, correlation_id=correlation_id))
            if status == CommandStatus.AWAITING_CONFIRMATION:
                uow.add_event(ConfirmationRequired(command_id=dto.command_id, device_id=entity.device_id, expires_at=expires_at, correlation_id=correlation_id))

        if status == CommandStatus.APPROVED:
            await self._dispatch(entity)
        return CommandDto.model_validate(entity)

    async def _dispatch(self, command: CommandEntity) -> None:
        try:
            await self._dispatcher.dispatch(command)
            async with self._uow() as uow:
                stored = await uow.commands.get_by_command_id(command.command_id, lock=True)
                if stored is None:
                    return
                transition_status(stored, CommandStatus.DISPATCHED)
                stored.dispatched_at = datetime.now(timezone.utc)
                uow.add_event(CommandResolved(command_id=stored.command_id, device_id=stored.device_id, status=CommandStatus.DISPATCHED, action=stored.action, reasons=tuple(stored.decision_reasons)))
        except Exception:
            async with self._uow() as uow:
                stored = await uow.commands.get_by_command_id(command.command_id, lock=True)
                if stored is not None:
                    transition_status(stored, CommandStatus.DISPATCHED)
                    stored.dispatched_at = datetime.now(timezone.utc)
                    transition_status(stored, CommandStatus.FAILED)
                    uow.add_event(CommandResolved(
                        command_id=stored.command_id,
                        device_id=stored.device_id,
                        status=CommandStatus.FAILED,
                        action=stored.action,
                        reasons=tuple(stored.decision_reasons),
                    ))
                    await uow.audit.record(actor="system", action="command.dispatch_failed", target=str(stored.command_id), details={"action": stored.action})

    async def get(self, actor: Principal, command_id: UUID) -> CommandDto:
        require(actor, Permission.COMMAND_READ)
        async with self._uow() as uow:
            entity = await uow.commands.get_by_command_id(command_id)
            if entity is None:
                raise CommandNotFound(command_id)
            return CommandDto.model_validate(entity)

    async def confirm(self, actor: Principal, command_id: UUID) -> CommandDto:
        require(actor, Permission.COMMAND_CONFIRM)
        if actor.role not in {Role.ADMIN, Role.USER}:
            raise HumanConfirmationRequired()
        async with self._uow() as uow:
            entity = await uow.commands.get_by_command_id(command_id, lock=True)
            if entity is None:
                raise CommandNotFound(command_id)
            if entity.expires_at is not None and entity.expires_at <= datetime.now(timezone.utc):
                transition_status(entity, CommandStatus.EXPIRED)
            else:
                transition_status(entity, CommandStatus.APPROVED)
            uow.add_event(CommandResolved(command_id=entity.command_id, device_id=entity.device_id, status=entity.status, action=entity.action, reasons=tuple(entity.decision_reasons)))
            await uow.audit.record(actor=actor.id, action="command.confirm", target=str(command_id), details={"status": entity.status.value})
        if entity.status == CommandStatus.APPROVED:
            await self._dispatch(entity)
        return await self.get(actor, command_id)

    async def reject(self, actor: Principal, command_id: UUID) -> CommandDto:
        require(actor, Permission.COMMAND_CONFIRM)
        if actor.role not in {Role.ADMIN, Role.USER}:
            raise HumanConfirmationRequired()
        async with self._uow() as uow:
            entity = await uow.commands.get_by_command_id(command_id, lock=True)
            if entity is None:
                raise CommandNotFound(command_id)
            transition_status(entity, CommandStatus.REJECTED)
            uow.add_event(CommandResolved(command_id=entity.command_id, device_id=entity.device_id, status=entity.status, action=entity.action, reasons=tuple(entity.decision_reasons)))
            await uow.audit.record(actor=actor.id, action="command.reject", target=str(command_id), details={})
            return CommandDto.model_validate(entity)

    async def on_ack(self, actor: Principal, command_id: UUID, ok: bool) -> CommandDto:
        require(actor, Permission.DEVICE_REPORT)
        async with self._uow() as uow:
            entity = await uow.commands.get_by_command_id(command_id, lock=True)
            if entity is None:
                raise CommandNotFound(command_id)
            transition_status(entity, CommandStatus.ACKNOWLEDGED if ok else CommandStatus.FAILED)
            entity.acked_at = datetime.now(timezone.utc)
            uow.add_event(CommandResolved(
                command_id=entity.command_id,
                device_id=entity.device_id,
                status=entity.status,
                action=entity.action,
                reasons=tuple(entity.decision_reasons),
            ))
            await uow.audit.record(
                actor=actor.id,
                action="command.ack" if ok else "command.ack_failed",
                target=str(command_id),
                details={"status": entity.status.value},
            )
            return CommandDto.model_validate(entity)

    async def emergency_stop(self, actor: Principal) -> None:
        require(actor, Permission.SYSTEM_EMERGENCY)
        async with self._uow() as uow:
            state = await uow.commands.system_state()
            state.emergency_stop = True
            for entity in await uow.commands.awaiting_confirmation():
                transition_status(entity, CommandStatus.CANCELLED)
                uow.add_event(CommandResolved(
                    command_id=entity.command_id,
                    device_id=entity.device_id,
                    status=CommandStatus.CANCELLED,
                    action=entity.action,
                    reasons=tuple(entity.decision_reasons),
                ))
            await uow.audit.record(actor=actor.id, action="system.emergency_stop.activate", target="global", details={})
            uow.add_event(EmergencyStopActivated(activated_by=actor.id))

    async def clear_emergency_stop(self, actor: Principal) -> None:
        require(actor, Permission.SYSTEM_EMERGENCY)
        async with self._uow() as uow:
            state = await uow.commands.system_state()
            state.emergency_stop = False
            await uow.audit.record(actor=actor.id, action="system.emergency_stop.clear", target="global", details={})

    async def expire_confirmations(self) -> int:
        now = datetime.now(timezone.utc)
        expired_count = 0
        async with self._uow() as uow:
            for entity in await uow.commands.awaiting_confirmation():
                if entity.expires_at is not None and entity.expires_at <= now:
                    transition_status(entity, CommandStatus.EXPIRED)
                    uow.add_event(CommandResolved(
                        command_id=entity.command_id,
                        device_id=entity.device_id,
                        status=CommandStatus.EXPIRED,
                        action=entity.action,
                        reasons=tuple(entity.decision_reasons),
                    ))
                    expired_count += 1
        return expired_count

    async def timeout_dispatched(self, timeout_seconds: int = 60) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
        timed_out_count = 0
        async with self._uow() as uow:
            for entity in await uow.commands.dispatched_before(cutoff):
                transition_status(entity, CommandStatus.TIMED_OUT)
                uow.add_event(CommandResolved(
                    command_id=entity.command_id,
                    device_id=entity.device_id,
                    status=CommandStatus.TIMED_OUT,
                    action=entity.action,
                    reasons=tuple(entity.decision_reasons),
                ))
                timed_out_count += 1
        return timed_out_count

    async def redeliver_approved(self) -> int:
        delivered = 0
        async with self._uow() as uow:
            approved = await uow.commands.approved()
        for entity in approved:
            await self._dispatch(entity)
            delivered += 1
        return delivered

    async def cancel(self, actor: Principal, command_id: UUID) -> CommandDto:
        require(actor, Permission.COMMAND_CONFIRM)
        async with self._uow() as uow:
            entity = await uow.commands.get_by_command_id(command_id, lock=True)
            if entity is None:
                raise CommandNotFound(command_id)
            transition_status(entity, CommandStatus.CANCELLED)
            uow.add_event(CommandResolved(
                command_id=entity.command_id,
                device_id=entity.device_id,
                status=entity.status,
                action=entity.action,
                reasons=tuple(entity.decision_reasons),
            ))
            await uow.audit.record(actor=actor.id, action="command.cancel", target=str(command_id), details={})
            return CommandDto.model_validate(entity)
