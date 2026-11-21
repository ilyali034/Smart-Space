import asyncio
import json

from typing import Any
from uuid import UUID

import aiomqtt

from device_simulator.sensors.dtos.sensor import SimulatedSensor

class RoomSimulation:
    def __init__(
        self,
        room_name: str,
        *,
        publisher: Any | None = None,
        topic_prefix: str = "smart-space/devices",
        interval: float = 3.0,
    ) -> None:
        self.room_name = room_name
        self._publisher = publisher
        self._topic_prefix = topic_prefix.strip("/")
        self._interval = interval
        self._sensors: dict[UUID, SimulatedSensor] = {}
        self._running = False

    async def add_sensor(
        self,
        device_id: UUID | str,
        slug: str,
        *,
        sensor_type: str = "climate",
        temperature: float = 21.5,
        humidity: float = 45.0,
        target_temperature: float | None = None,
        power: bool = True,
        online: bool = True,
    ) -> SimulatedSensor:
        uid = UUID(str(device_id))
        sensor = SimulatedSensor(
            device_id=uid,
            slug=slug,
            sensor_type=sensor_type,
            temperature=temperature,
            humidity=humidity,
            target_temperature=target_temperature,
            power=power,
            online=online,
        )
        self._sensors[uid] = sensor

        if self._publisher is not None:
            await self._publisher.publish_status(uid, online=online)

        return sensor

    async def set_sensor_online(self, device_id: UUID | str, online: bool) -> None:
        uid = UUID(str(device_id))
        sensor = self._sensors.get(uid)
        if sensor is None:
            return
        sensor.online = online
        if self._publisher is not None:
            await self._publisher.publish_status(uid, online=online)

    async def run_telemetry_loop(self) -> None:
        self._running = True
        while self._running:
            for sensor in self._sensors.values():
                readings = sensor.tick(self._interval)
                if readings is not None and self._publisher is not None:
                    await self._publisher.publish_telemetry(
                        sensor.device_id,
                        {"room": self.room_name, **readings},
                    )
            await asyncio.sleep(self._interval)

    async def listen_commands(self, mqtt_client: aiomqtt.Client) -> None:
        await mqtt_client.subscribe(f"{self._topic_prefix}/+/commands", qos=1)
        async for message in mqtt_client.messages:
            try:
                data = json.loads(message.payload.decode("utf-8"))
            except Exception:
                continue

            raw_device_id = data.get("device_id")
            if not raw_device_id:
                continue

            uid = UUID(str(raw_device_id))
            sensor = self._sensors.get(uid)
            if sensor is None:
                continue

            command_id = data.get("command_id")
            action = str(data.get("action", ""))
            parameters = data.get("parameters") or {}

            ok = sensor.apply_command(action, parameters)
            ack_payload = json.dumps(
                {
                    "command_id": command_id,
                    "device_id": str(uid),
                    "ok": ok,
                },
                separators=(",", ":"),
            )
            await mqtt_client.publish(
                f"{self._topic_prefix}/{uid}/ack",
                ack_payload,
                qos=1,
                retain=False,
            )

    def stop(self) -> None:
        self._running = False