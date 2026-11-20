from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend_engine.shared.storage.database import Base


class CommandStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    DISPATCHED = "dispatched"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


TRANSITIONS: dict[CommandStatus, frozenset[CommandStatus]] = {
    CommandStatus.PENDING: frozenset({CommandStatus.APPROVED, CommandStatus.REJECTED, CommandStatus.AWAITING_CONFIRMATION}),
    CommandStatus.AWAITING_CONFIRMATION: frozenset({CommandStatus.APPROVED, CommandStatus.REJECTED, CommandStatus.EXPIRED, CommandStatus.CANCELLED}),
    CommandStatus.APPROVED: frozenset({CommandStatus.DISPATCHED, CommandStatus.CANCELLED}),
    CommandStatus.DISPATCHED: frozenset({CommandStatus.ACKNOWLEDGED, CommandStatus.FAILED, CommandStatus.TIMED_OUT}),
}

TERMINAL_STATUSES = frozenset({CommandStatus.REJECTED, CommandStatus.EXPIRED, CommandStatus.CANCELLED, CommandStatus.ACKNOWLEDGED, CommandStatus.FAILED, CommandStatus.TIMED_OUT})


class InvalidStatusTransition(Exception):
    pass


def transition_status(entity: "CommandEntity", new_status: CommandStatus) -> None:
    old_status = entity.status
    if old_status in TERMINAL_STATUSES:
        raise InvalidStatusTransition(f"{old_status} is terminal")
    if new_status not in TRANSITIONS.get(old_status, frozenset()):
        raise InvalidStatusTransition(f"invalid transition: {old_status} -> {new_status}")
    entity.status = new_status
    entity.updated_at = datetime.now().astimezone()


class CommandEntity(Base):
    __tablename__ = "command"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    command_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    device_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(64))
    parameters: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    status: Mapped[CommandStatus] = mapped_column(String(32), default=CommandStatus.PENDING)
    source: Mapped[str] = mapped_column(String(16))
    requested_by: Mapped[str] = mapped_column(String(64))
    decision_reasons: Mapped[list[str]] = mapped_column(JSONB, default=list)
    correlation_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("command_id", name="uq_command_command_id"),
        Index("ix_command_device_created", "device_id", "created_at"),
        Index("ix_command_status", "status"),
    )


class SystemStateEntity(Base):
    __tablename__ = "system_state"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    emergency_stop: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
