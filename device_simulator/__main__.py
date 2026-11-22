import asyncio
import json
import os
import uuid
from uuid import UUID

import aiomqtt

from device_simulator.mqtt.publisher import SensorsSimulationMQTTPublisher
from device_simulator.sensors.rooms import RoomSimulation


def _parse_uuid_env(name: str) -> UUID:
    raw = os.getenv(name)
    return UUID(raw) if raw else uuid.uuid4()


async def _listen_commands(
    client: aiomqtt.Client,
    room: RoomSimulation,
    prefix: str,
) -> None:
    clean_prefix = prefix.strip("/")
    await client.subscribe(f"{clean_prefix}/+/commands", qos=1)

    async for message in client.messages:
        try:
            data = json.loads(message.payload.decode("utf-8"))
        except Exception:
            continue

        raw_device_id = data.get("device_id")
        if not raw_device_id:
            continue

        try:
            device_id = UUID(str(raw_device_id))
        except ValueError:
            continue

        sensor = room._sensors.get(device_id)
        if sensor is None:
            continue

        command_id = data.get("command_id")
        action = str(data.get("action", ""))
        parameters = data.get("parameters") or {}

        ok = sensor.apply_command(action, parameters)
        ack_payload = json.dumps(
            {
                "command_id": command_id,
                "device_id": str(device_id),
                "ok": ok,
            },
            separators=(",", ":"),
        )
        await client.publish(
            f"{clean_prefix}/{device_id}/ack",
            ack_payload,
            qos=1,
            retain=False,
        )


async def main() -> None:
    hostname = os.getenv("MQTT_HOST", "localhost")
    port = int(os.getenv("MQTT_PORT", "1883"))
    username = os.getenv("MQTT_USERNAME")
    password = os.getenv("MQTT_PASSWORD")
    prefix = os.getenv("MQTT_TOPIC_PREFIX", "smart-space/devices")
    interval = float(os.getenv("SIM_INTERVAL", "3.0"))

    temp_id = _parse_uuid_env("SIM_TEMP_DEVICE_ID")
    humidity_id = _parse_uuid_env("SIM_HUMIDITY_DEVICE_ID")

    while True:
        try:
            async with aiomqtt.Client(
                hostname=hostname,
                port=port,
                username=username,
                password=password,
            ) as client:
                publisher = SensorsSimulationMQTTPublisher(
                    hostname=hostname,
                    port=port,
                    username=username,
                    password=password,
                    topic_prefix=prefix,
                )
                publisher._client = client

                room = RoomSimulation("living_room", publisher=publisher, topic_prefix=prefix, interval=interval)
                await room.add_sensor(
                    temp_id,
                    "living_room_temp",
                    temperature=21.5,
                    humidity=45.0,
                    target_temperature=22.0,
                )
                await room.add_sensor(
                    humidity_id,
                    "living_room_humidity",
                    sensor_type="humidity",
                    temperature=20.0,
                    humidity=50.0,
                )

                listener = asyncio.create_task(_listen_commands(client, room, prefix))
                try:
                    await room.run_telemetry_loop()
                finally:
                    room.stop()
                    listener.cancel()
                    try:
                        await listener
                    except asyncio.CancelledError:
                        pass
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[SIMULATOR] MQTT connection error: {exc}. Reconnecting in 3s...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[SIMULATOR] Stopped.")