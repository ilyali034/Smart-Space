import json
import ssl
from typing import Protocol

import aiomqtt

from backend_engine.modules.commands.entity import CommandEntity


class CommandDispatcher(Protocol):
    async def dispatch(self, command: CommandEntity) -> None: ...


class MqttCommandDispatcher:
    def __init__(
        self,
        *,
        hostname: str,
        port: int = 1883,
        username: str | None = None,
        password: str | None = None,
        topic_prefix: str = "smart-space/devices",
        tls: bool = False,
        keepalive: int = 30,
    ) -> None:
        self._hostname = hostname
        self._port = port
        self._username = username
        self._password = password
        self._topic_prefix = topic_prefix.strip("/")
        self._tls_context = ssl.create_default_context() if tls else None
        self._keepalive = keepalive

    async def dispatch(self, command: CommandEntity) -> None:
        topic = f"{self._topic_prefix}/{command.device_id}/commands"
        payload = json.dumps(
            {
                "command_id": str(command.command_id),
                "device_id": str(command.device_id),
                "action": command.action,
                "parameters": command.parameters,
                "correlation_id": (
                    str(command.correlation_id)
                    if command.correlation_id is not None
                    else None
                ),
            },
            separators=(",", ":"),
        )
        async with aiomqtt.Client(
            hostname=self._hostname,
            port=self._port,
            username=self._username,
            password=self._password,
            tls_context=self._tls_context,
            keepalive=self._keepalive,
        ) as client:
            await client.publish(topic, payload, qos=1, retain=False)
