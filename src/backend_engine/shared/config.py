import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

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
        )
