import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GatewayConfig:
    api_url: str = "http://localhost:8000"
    api_token: str = ""  # token with role "gateway"
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_tls: bool = False
    mqtt_keepalive: int = 30
    topic_prefix: str = "smart-space/devices"
    heartbeat_seconds: float = 10.0  # re-send unchanged state at most this often (keeps last_seen fresh)

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        token = os.getenv("GATEWAY_API_TOKEN", "")
        if not token:
            raise RuntimeError("GATEWAY_API_TOKEN is not set (create one: scripts/create_token.py --role gateway)")
        return cls(
            api_url=os.getenv("GATEWAY_API_URL", "http://localhost:8000").rstrip("/"),
            api_token=token,
            mqtt_host=os.getenv("MQTT_HOST", "localhost"),
            mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
            mqtt_username=os.getenv("MQTT_USERNAME") or None,
            mqtt_password=os.getenv("MQTT_PASSWORD") or None,
            mqtt_tls=os.getenv("MQTT_TLS", "false").lower() == "true",
            mqtt_keepalive=int(os.getenv("MQTT_KEEPALIVE", "30")),
            topic_prefix=os.getenv("MQTT_TOPIC_PREFIX", "smart-space/devices").strip("/"),
            heartbeat_seconds=float(os.getenv("GATEWAY_HEARTBEAT_SECONDS", "10")),
        )
