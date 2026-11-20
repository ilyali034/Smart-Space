import json
from uuid import uuid4

import pytest

from backend_engine.modules.commands.dispatcher import MqttCommandDispatcher
from backend_engine.modules.commands.entity import CommandEntity
from backend_engine.shared.config import Settings


def test_settings_load_mqtt_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/smart_space")
    monkeypatch.setenv("MQTT_HOST", "broker.example.test")
    monkeypatch.setenv("MQTT_PORT", "8883")
    monkeypatch.setenv("MQTT_USERNAME", "backend")
    monkeypatch.setenv("MQTT_PASSWORD", "secret")
    monkeypatch.setenv("MQTT_TOPIC_PREFIX", "building/devices")
    monkeypatch.setenv("MQTT_TLS", "true")
    monkeypatch.setenv("MQTT_KEEPALIVE", "45")

    settings = Settings.from_env()

    assert settings.mqtt_host == "broker.example.test"
    assert settings.mqtt_port == 8883
    assert settings.mqtt_username == "backend"
    assert settings.mqtt_password == "secret"
    assert settings.mqtt_topic_prefix == "building/devices"
    assert settings.mqtt_tls is True
    assert settings.mqtt_keepalive == 45


@pytest.mark.asyncio
async def test_mqtt_dispatcher_publishes_command(monkeypatch: pytest.MonkeyPatch) -> None:
    device_id = uuid4()
    command_id = uuid4()
    correlation_id = uuid4()
    command = CommandEntity(
        command_id=command_id,
        device_id=device_id,
        action="set_brightness",
        parameters={"brightness": 45},
        source="api",
        requested_by="test",
        correlation_id=correlation_id,
    )
    published: dict[str, object] = {}
    client_options: dict[str, object] = {}

    class FakeMqttClient:
        def __init__(self, **kwargs: object) -> None:
            client_options.update(kwargs)

        async def __aenter__(self) -> "FakeMqttClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def publish(
            self, topic: str, payload: str, *, qos: int, retain: bool
        ) -> None:
            published.update(
                topic=topic, payload=payload, qos=qos, retain=retain
            )

    monkeypatch.setattr(
        "backend_engine.modules.commands.dispatcher.aiomqtt.Client",
        FakeMqttClient,
    )
    mqtt_dispatcher = MqttCommandDispatcher(
        hostname="mqtt.example.test",
        port=8883,
        username="backend",
        password="secret",
        topic_prefix="building/devices/",
        tls=True,
    )

    await mqtt_dispatcher.dispatch(command)

    assert published["topic"] == f"building/devices/{device_id}/commands"
    assert json.loads(str(published["payload"])) == {
        "command_id": str(command_id),
        "device_id": str(device_id),
        "action": "set_brightness",
        "parameters": {"brightness": 45},
        "correlation_id": str(correlation_id),
    }
    assert published["qos"] == 1
    assert published["retain"] is False
    assert client_options["hostname"] == "mqtt.example.test"
    assert client_options["port"] == 8883
    assert client_options["username"] == "backend"
    assert client_options["password"] == "secret"
    assert client_options["tls_context"] is not None