from uuid import UUID

from backend_engine.modules.commands.entity import CommandStatus
from backend_engine.shared.events.base import Event


class CommandResolved(Event):
    command_id: UUID
    device_id: UUID
    status: CommandStatus
    action: str
    reasons: tuple[str, ...] = ()


class ConfirmationRequired(Event):
    command_id: UUID
    device_id: UUID
    expires_at: object


class EmergencyStopActivated(Event):
    activated_by: str
