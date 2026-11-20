from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class CommandSource(StrEnum):
    API = "api"
    AI = "ai"
    AUTOMATION = "automation"


@dataclass(frozen=True)
class CommandRequest:
    action: str
    parameters: dict[str, Any]
    source: CommandSource


@dataclass(frozen=True)
class SafetyContext:
    device_exists: bool
    device_enabled: bool
    device_online: bool
    device_type: str
    device_capabilities: tuple[str, ...]
    emergency_stop: bool = False
    recent_command_count: int = 0
    rate_limit: int = 100
    active_conflicting_commands: tuple[str, ...] = ()
