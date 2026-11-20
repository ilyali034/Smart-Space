from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]{3,64}$")]
Name = Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)]


class DeviceType(StrEnum):
    TEMPERATURE_SENSOR = "temperature_sensor"
    HUMIDITY_SENSOR = "humidity_sensor"
    MOTION_SENSOR = "motion_sensor"
    LIGHT_SENSOR = "light_sensor"
    DOOR_SENSOR = "door_sensor"
    WINDOW_SENSOR = "window_sensor"
    SMART_LIGHT = "smart_light"
    SMART_RELAY = "smart_relay"
    SMART_PLUG = "smart_plug"
    SMART_SPEAKER = "smart_speaker"
    CUSTOM = "custom"


class Availability(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class CreateDeviceDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: Slug
    name: Name
    type: DeviceType
    room_id: UUID | None = None
    capabilities: list[str] = Field(default_factory=list, max_length=32)


class DeviceDto(BaseModel):
    """Module boundary. ORM entities never leave the devices module."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    slug: str
    name: str
    type: DeviceType
    room_id: UUID | None
    enabled: bool
    availability: Availability
    capabilities: list[str]
    state: dict[str, object]
    firmware_version: str | None
    last_seen_at: datetime | None
