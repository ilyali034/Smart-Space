from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Risk(StrEnum):
    LOW = "low"
    CONFIRM = "confirm"


class NoParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BrightnessParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    brightness: int = Field(strict=True, ge=0, le=100)


class ActionSpec:
    def __init__(self, capability: str, params: type[BaseModel], risk: Risk = Risk.LOW) -> None:
        self.capability = capability
        self.params = params
        self.risk = risk


ACTIONS: dict[str, ActionSpec] = {
    "turn_on": ActionSpec("on_off", NoParams),
    "turn_off": ActionSpec("on_off", NoParams),
    "set_brightness": ActionSpec("brightness", BrightnessParams),
}
