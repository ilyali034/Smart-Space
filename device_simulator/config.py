import json
import os
import uuid
from dataclasses import dataclass, field
from uuid import UUID

_NS = uuid.UUID("0c3a5a7e-2b1f-4a53-9d4e-5a1d6f0c9e11")


@dataclass(frozen=True, slots=True)
class SimConfig:
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_keepalive: int = 30
    topic_prefix: str = "smart-space/devices"
    interval: float = 3.0
    fleets: tuple[str, ...] = ("living_room",)
    # Registers the devices in the backend and uses the ids it assigns. Needs a token
    # with device:read + device:write (role user or admin).
    api_url: str | None = None
    api_token: str | None = None
    fixed_ids: dict[str, UUID] = field(default_factory=dict)  # SIM_DEVICE_IDS='{"slug":"uuid"}'

    @property
    def can_provision(self) -> bool:
        return bool(self.api_url and self.api_token)

    @classmethod
    def from_env(cls) -> "SimConfig":
        raw_ids = json.loads(os.getenv("SIM_DEVICE_IDS", "{}") or "{}")
        return cls(
            mqtt_host=os.getenv("MQTT_HOST", "localhost"),
            mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
            mqtt_username=os.getenv("MQTT_USERNAME") or None,
            mqtt_password=os.getenv("MQTT_PASSWORD") or None,
            mqtt_keepalive=int(os.getenv("MQTT_KEEPALIVE", "30")),
            topic_prefix=os.getenv("MQTT_TOPIC_PREFIX", "smart-space/devices").strip("/"),
            interval=float(os.getenv("SIM_INTERVAL", "3.0")),
            fleets=tuple(x.strip() for x in os.getenv("SIM_FLEET", "living_room").split(",") if x.strip()),
            api_url=(os.getenv("SIM_API_URL") or "").rstrip("/") or None,
            api_token=os.getenv("SIM_API_TOKEN") or None,
            fixed_ids={k: UUID(v) for k, v in raw_ids.items()},
        )


def fallback_id(slug: str) -> UUID:
    """Stable id when the backend is not used. It will NOT match a backend-created device."""
    return uuid.uuid5(_NS, slug)
