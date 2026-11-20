from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend_engine.shared.storage.database import Base


class DeviceEntity(Base):
    __tablename__ = "device"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(32))
    room_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    availability: Mapped[str] = mapped_column(
        String(16), default="unknown", server_default="unknown"
    )
    capabilities: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    state: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, server_default="{}")
    firmware_version: Mapped[str | None] = mapped_column(String(32))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("slug", name="uq_device_slug"),
        Index("ix_device_room_id", "room_id"),
    )
