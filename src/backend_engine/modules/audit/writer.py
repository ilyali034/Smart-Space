from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend_engine.modules.audit.entity import AuditLogEntity


class SqlAlchemyAuditWriter:
    """Writes in the caller's transaction: no audit row, no change."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        actor: str,
        action: str,
        target: str,
        correlation_id: UUID | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        self._session.add(
            AuditLogEntity(
                actor=actor,
                action=action,
                target=target,
                correlation_id=correlation_id,
                details=details or {},
            )
        )
