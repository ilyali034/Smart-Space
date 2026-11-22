"""Virtual devices. Command semantics mirror the backend's Safety action table
(turn_on / turn_off / set_brightness); anything else is refused like real firmware would."""

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from device_simulator.faults import Faults


@dataclass
class SimDevice:
    slug: str
    device_type: str
    capabilities: tuple[str, ...] = ()
    device_id: UUID | None = None  # assigned by the backend (provisioning)
    online: bool = True
    faults: Faults = field(default_factory=Faults)

    def state(self) -> dict[str, Any]:
        return {}

    def apply_command(self, action: str, parameters: dict[str, Any]) -> bool:
        return False

    def set_state(self, patch: dict[str, Any]) -> bool:
        """Change state from outside (a person pressing a button, weather...)."""
        return False

    def tick(self, dt: float) -> None:
        """Advance internal simulation (drift etc.)."""


@dataclass
class SmartLight(SimDevice):
    power: bool = False
    brightness: int = 100

    def state(self) -> dict[str, Any]:
        return {"power": self.power, "brightness": self.brightness}

    def apply_command(self, action: str, parameters: dict[str, Any]) -> bool:
        if action in ("turn_on", "turn_off") and not parameters:
            self.power = action == "turn_on"
            return True
        if action == "set_brightness" and set(parameters) == {"brightness"}:
            value = parameters["brightness"]
            if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 100:
                self.brightness = value
                return True
        return False

    def set_state(self, patch: dict[str, Any]) -> bool:
        ok = False
        if isinstance(patch.get("power"), bool):
            self.power, ok = patch["power"], True
        b = patch.get("brightness")
        if isinstance(b, int) and not isinstance(b, bool) and 0 <= b <= 100:
            self.brightness, ok = b, True
        return ok


@dataclass
class SmartSwitch(SimDevice):
    """Relay / plug: on-off only."""

    power: bool = False

    def state(self) -> dict[str, Any]:
        return {"power": self.power}

    def apply_command(self, action: str, parameters: dict[str, Any]) -> bool:
        if action in ("turn_on", "turn_off") and not parameters:
            self.power = action == "turn_on"
            return True
        return False

    def set_state(self, patch: dict[str, Any]) -> bool:
        if isinstance(patch.get("power"), bool):
            self.power = patch["power"]
            return True
        return False


@dataclass
class ClimateSensor(SimDevice):
    """Reports only what its capabilities say (temperature and/or humidity)."""

    temperature: float = 21.5
    humidity: float = 45.0

    def _keys(self) -> list[str]:
        keys = [k for k in ("temperature", "humidity") if k in self.capabilities]
        return keys or ["temperature", "humidity"]

    def state(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self._keys()}

    def tick(self, dt: float) -> None:
        if "temperature" in self._keys():
            self.temperature = round(self.temperature + random.uniform(-0.15, 0.15), 2)
        if "humidity" in self._keys():
            self.humidity = round(max(10.0, min(95.0, self.humidity + random.uniform(-0.5, 0.5))), 1)

    def set_state(self, patch: dict[str, Any]) -> bool:
        ok = False
        for key, lo, hi in (("temperature", -40.0, 85.0), ("humidity", 0.0, 100.0)):
            v = patch.get(key)
            if key in self._keys() and isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi:
                setattr(self, key, float(v))
                ok = True
        return ok


@dataclass(frozen=True)
class DeviceSpec:
    slug: str
    device_type: str  # backend DeviceType value
    capabilities: tuple[str, ...]
    factory: Callable[..., SimDevice]

    def build(self) -> SimDevice:
        return self.factory(slug=self.slug, device_type=self.device_type, capabilities=self.capabilities)


FLEETS: dict[str, list[DeviceSpec]] = {
    "living_room": [
        DeviceSpec("living_lamp", "smart_light", ("on_off", "brightness"), SmartLight),
        DeviceSpec("living_relay", "smart_relay", ("on_off",), SmartSwitch),  # risky: needs human confirmation
        DeviceSpec("living_temp", "temperature_sensor", ("temperature",), ClimateSensor),
        DeviceSpec("living_humidity", "humidity_sensor", ("humidity",), ClimateSensor),
    ],
    "kitchen": [
        DeviceSpec("kitchen_light", "smart_light", ("on_off", "brightness"), SmartLight),
        DeviceSpec("kitchen_plug", "smart_plug", ("on_off",), SmartSwitch),  # risky: needs human confirmation
        DeviceSpec("kitchen_temp", "temperature_sensor", ("temperature",), ClimateSensor),
    ],
}


def build_fleet(names: list[str]) -> list[SimDevice]:
    devices: list[SimDevice] = []
    for name in names:
        if name not in FLEETS:
            raise ValueError(f"unknown fleet '{name}'. Available: {', '.join(FLEETS)}")
        devices.extend(spec.build() for spec in FLEETS[name])
    return devices
