from dataclasses import dataclass, field
from uuid import UUID 
from typing import Optional, Any 

import random

@dataclass
class SimulatedSensor:
    device_id: UUID
    slug: str
    sensor_type: str = "climate"  
    temperature: float = 21.5
    humidity: float = 45.0
    target_temperature: float | None = None
    power: bool = True
    online: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def tick(self, dt_seconds: float = 2.0) -> dict[str, Any] | None:
        if not self.online:
            return None

        if self.power and self.target_temperature is not None:
            diff = self.target_temperature - self.temperature
            self.temperature += max(-0.5, min(0.5, diff * 0.25 * (dt_seconds / 2.0)))

        if self.power:
            self.temperature = round(self.temperature + random.uniform(-0.15, 0.15), 2)
            self.humidity = round(max(10.0, min(95.0, self.humidity + random.uniform(-0.5, 0.5))), 1)

        return {
            "slug": self.slug,
            "type": self.sensor_type,
            "power": self.power,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "target_temperature": self.target_temperature,
        }

    def apply_command(self, action: str, parameters: dict[str, Any]) -> bool:
        if action == "set_power":
            self.power = bool(parameters.get("value", True))
            return True
        if action == "set_target_temperature" and "value" in parameters:
            self.target_temperature = float(parameters["value"])
            return True
        if action == "set_online":
            self.online = bool(parameters.get("value", True))
            return True
        return False