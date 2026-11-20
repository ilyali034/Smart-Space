import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_topic_prefix: str = "smart-space/devices"
    mqtt_tls: bool = False
    mqtt_keepalive: int = 30

    @classmethod
    def from_env(cls) -> "Settings":
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL is not set")
        return cls(
            database_url=url,
            db_echo=os.getenv("DB_ECHO", "false").lower() == "true",
            db_pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            db_max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            mqtt_host=os.getenv("MQTT_HOST", "localhost"),
            mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
            mqtt_username=os.getenv("MQTT_USERNAME") or None,
            mqtt_password=os.getenv("MQTT_PASSWORD") or None,
            mqtt_topic_prefix=os.getenv(
                "MQTT_TOPIC_PREFIX", "smart-space/devices"
            ),
            mqtt_tls=os.getenv("MQTT_TLS", "false").lower() == "true",
            mqtt_keepalive=int(os.getenv("MQTT_KEEPALIVE", "30")),
        )
