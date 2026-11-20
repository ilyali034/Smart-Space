import hashlib
import secrets
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from backend_engine.shared.auth.principal import Principal, Role
from backend_engine.shared.storage.database import Base


class ApiTokenEntity(Base):
    __tablename__ = "api_token"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    role: Mapped[str] = mapped_column(String(16))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


def hash_token(raw: str) -> str:
    # Tokens are 256-bit random, so a fast hash is sufficient (not for passwords).
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_token() -> tuple[str, str]:
    """Returns (raw, hash). Show raw once, store only hash."""
    raw = "ss_" + secrets.token_urlsafe(32)
    return raw, hash_token(raw)


class TokenVerifier:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def verify(self, raw: str) -> Principal | None:
        async with self._factory() as session:
            row = (
                await session.execute(
                    select(ApiTokenEntity).where(ApiTokenEntity.token_hash == hash_token(raw))
                )
            ).scalar_one_or_none()
        if row is None or row.revoked_at is not None:
            return None
        if row.expires_at is not None and row.expires_at <= datetime.now(timezone.utc):
            return None
        return Principal(id=str(row.id), role=Role(row.role))