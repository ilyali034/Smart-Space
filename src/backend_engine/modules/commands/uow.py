from sqlalchemy.ext.asyncio import AsyncSession

from backend_engine.modules.audit.writer import SqlAlchemyAuditWriter
from backend_engine.modules.commands.repository import SqlAlchemyCommandRepository
from backend_engine.shared.storage.uow import BaseUnitOfWork


class CommandsUnitOfWork(BaseUnitOfWork):
    commands: SqlAlchemyCommandRepository
    audit: SqlAlchemyAuditWriter

    def _bind(self, session: AsyncSession) -> None:
        self.commands = SqlAlchemyCommandRepository(session)
        self.audit = SqlAlchemyAuditWriter(session)
