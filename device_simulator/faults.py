from dataclasses import dataclass
from typing import Any, Literal

Outcome = Literal["ok", "fail", "drop"]

_LIMITS: dict[str, tuple[type, float]] = {
    "ack_delay": (float, 60.0),
    "fail_next": (int, 1000),
    "drop_next": (int, 1000),
}


@dataclass
class Faults:
    """Per-device failure injection (changeable at runtime via the control topic).

    ack_delay      seconds between executing a command and acknowledging it (slow network)
    fail_next      next N commands: device cannot execute -> ack with ok=false, state unchanged
    drop_next      next N commands: device executes but the ack is lost (never sent)
    duplicate_ack  every ack is sent twice (QoS 1 duplicates; the gateway must deduplicate)
    """

    ack_delay: float = 0.0
    fail_next: int = 0
    drop_next: int = 0
    duplicate_ack: bool = False

    def update(self, data: dict[str, Any]) -> list[str]:
        """Apply valid fields, return the names of ignored/invalid ones."""
        rejected: list[str] = []
        for key, value in data.items():
            if key == "duplicate_ack" and isinstance(value, bool):
                self.duplicate_ack = value
            elif key in _LIMITS and isinstance(value, (int, float)) and not isinstance(value, bool):
                typ, hi = _LIMITS[key]
                if 0 <= value <= hi:
                    setattr(self, key, typ(value))
                    continue
                rejected.append(key)
            else:
                rejected.append(key)
        return rejected

    def next_outcome(self) -> Outcome:
        if self.drop_next > 0:
            self.drop_next -= 1
            return "drop"
        if self.fail_next > 0:
            self.fail_next -= 1
            return "fail"
        return "ok"
