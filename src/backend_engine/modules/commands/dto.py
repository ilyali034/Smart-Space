from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend_engine.modules.commands.entity import CommandStatus
from backend_engine.modules.safety.types import CommandSource


class SubmitCommandDto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: UUID
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    source: CommandSource = CommandSource.API


class AckCommandDto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool


class CommandDto(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)
    id: UUID
    command_id: UUID
    device_id: UUID
    action: str
    parameters: dict[str, Any]
    status: CommandStatus
    source: CommandSource = CommandSource.API
    requested_by: str
    decision_reasons: list[str]
    correlation_id: UUID | None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    dispatched_at: datetime | None
    acked_at: datetime | None
