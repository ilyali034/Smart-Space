from uuid import UUID

from backend_engine.modules.devices.dto import Availability
from backend_engine.shared.events.base import Event


class DeviceStateChanged(Event):
    device_id: UUID
    slug: str
    room_id: UUID | None
    changed: dict[str, object]
    previous: dict[str, object]


class DeviceAvailabilityChanged(Event):
    device_id: UUID
    slug: str
    room_id: UUID | None
    availability: Availability
    previous: Availability
