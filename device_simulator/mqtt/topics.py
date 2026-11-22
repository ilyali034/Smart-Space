from uuid import UUID


class Topics:
    """Same layout as backend MqttCommandDispatcher / docs/mqtt-gateway.md."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix.strip("/")

    def commands(self, device_id: UUID | str) -> str:
        return f"{self.prefix}/{device_id}/commands"

    def telemetry(self, device_id: UUID | str) -> str:
        return f"{self.prefix}/{device_id}/telemetry"

    def status(self, device_id: UUID | str) -> str:
        return f"{self.prefix}/{device_id}/status"

    def ack(self, device_id: UUID | str) -> str:
        return f"{self.prefix}/{device_id}/ack"

    @property
    def control(self) -> str:
        """Simulator-only topic (not used by backend or gateway): inject faults, go offline..."""
        return f"{self.prefix}/_sim/control"
