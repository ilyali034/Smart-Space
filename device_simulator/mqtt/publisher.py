import asyncio
import json
import ssl
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import aiomqtt


class SensorsSimulationMQTTPublisher:
    def __init__(
        self,
        *,
        hostname: str = "localhost",
        port: int = 1883,
        username: str | None = None,
        password: str | None = None,
        topic_prefix: str = "smart-space/devices",
        client_id: str | None = None,
        tls: bool = False,
        keepalive: int = 30,
    ) -> None:
        self._hostname = hostname
        self._port = port
        self._username = username
        self._password = password
        self._topic_prefix = topic_prefix.strip("/")
        self._client_id = client_id
        self._tls_context = ssl.create_default_context() if tls else None
        self._keepalive = keepalive
        self._client: aiomqtt.Client | None = None

        self.topic = f"{self._topic_prefix}/+/telemetry"

    def build_telemetry_topic(self, device_id: UUID | str) -> str:
        return f"{self._topic_prefix}/{device_id}/telemetry"

    def build_status_topic(self, device_id: UUID | str) -> str:
        return f"{self._topic_prefix}/{device_id}/status"

    async def __aenter__(self) -> "SensorsSimulationMQTTPublisher":
        self._client = aiomqtt.Client(
            hostname=self._hostname,
            port=self._port,
            username=self._username,
            password=self._password,
            identifier=self._client_id,
            tls_context=self._tls_context,
            keepalive=self._keepalive,
        )
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc, tb)
            self._client = None

    async def publish_telemetry(
        self,
        device_id: UUID | str,
        readings: dict[str, Any],
        *,
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        if self._client is None:
            raise RuntimeError("Publisher is not connected. Use 'async with SensorsSimulationMQTTPublisher(...) as pub:'.")

        topic = self.build_telemetry_topic(device_id)
        payload = json.dumps(
            {
                "device_id": str(device_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "readings": readings,
            },
            separators=(",", ":"),
        )
        await self._client.publish(topic, payload, qos=qos, retain=retain)

    async def publish_status(
        self,
        device_id: UUID | str,
        online: bool,
        *,
        qos: int = 1,
        retain: bool = True,
    ) -> None:
        if self._client is None:
            raise RuntimeError("Publisher is not connected. Use 'async with SensorsSimulationMQTTPublisher(...) as pub:'.")

        topic = self.build_status_topic(device_id)
        payload = json.dumps(
            {
                "device_id": str(device_id),
                "online": online,
                "availability": "online" if online else "offline",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            separators=(",", ":"),
        )
        await self._client.publish(topic, payload, qos=qos, retain=retain)