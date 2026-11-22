"""Run:  GATEWAY_API_TOKEN=ss_... python -m device_gateway"""

import asyncio
import logging

import aiomqtt
import httpx

from device_gateway.backend import BackendClient
from device_gateway.config import GatewayConfig
from device_gateway.handler import GatewayHandler

log = logging.getLogger("device_gateway")


async def serve(handler: GatewayHandler, cfg: GatewayConfig, *, identifier: str = "smart-space-gateway") -> None:
    """MQTT loop: reconnects forever with capped exponential backoff."""
    delay = 1.0
    while True:
        try:
            async with aiomqtt.Client(
                hostname=cfg.mqtt_host,
                port=cfg.mqtt_port,
                username=cfg.mqtt_username,
                password=cfg.mqtt_password,
                keepalive=cfg.mqtt_keepalive,
                identifier=identifier,
            ) as client:
                for sub in handler.subscriptions:
                    await client.subscribe(sub, qos=1)
                log.info("connected to %s:%s, listening on %s", cfg.mqtt_host, cfg.mqtt_port, handler.subscriptions)
                delay = 1.0
                async for message in client.messages:
                    await handler.handle(str(message.topic), bytes(message.payload))  # type: ignore[arg-type]
        except aiomqtt.MqttError as exc:
            log.warning("MQTT connection lost (%s); retrying in %.0fs", exc, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30.0)


async def run(cfg: GatewayConfig) -> None:
    async with httpx.AsyncClient(
        base_url=cfg.api_url,
        headers={"Authorization": f"Bearer {cfg.api_token}"},
        timeout=httpx.Timeout(5.0, connect=3.0),
    ) as http:
        handler = GatewayHandler(
            BackendClient(http), topic_prefix=cfg.topic_prefix, heartbeat_seconds=cfg.heartbeat_seconds
        )
        await serve(handler, cfg)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run(GatewayConfig.from_env()))
    except KeyboardInterrupt:
        log.info("stopped")


if __name__ == "__main__":
    main()
