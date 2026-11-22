import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import aiomqtt

from device_simulator.mqtt.topics import Topics


def status_payload(device_id: UUID, online: bool) -> str:
    return json.dumps(
        {
            "device_id": str(device_id),
            "online": online,
            "availability": "online" if online else "offline",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        separators=(",", ":"),
    )


class DevicePublisher:
    """Publishes one device's messages over its own connection."""

    def __init__(self, client: aiomqtt.Client, topics: Topics, device_id: UUID) -> None:
        self._client = client
        self._topics = topics
        self._id = device_id

    async def status(self, online: bool) -> None:
        # retained: whoever subscribes later still learns the current state
        await self._client.publish(self._topics.status(self._id), status_payload(self._id, online), qos=1, retain=True)

    async def telemetry(self, readings: dict[str, Any]) -> None:
        payload = json.dumps(
            {"device_id": str(self._id), "timestamp": datetime.now(timezone.utc).isoformat(), "readings": readings},
            separators=(",", ":"),
        )
        await self._client.publish(self._topics.telemetry(self._id), payload, qos=1, retain=False)

    async def ack(self, command_id: str, ok: bool) -> None:
        payload = json.dumps({"command_id": command_id, "device_id": str(self._id), "ok": ok}, separators=(",", ":"))
        await self._client.publish(self._topics.ack(self._id), payload, qos=1, retain=False)
