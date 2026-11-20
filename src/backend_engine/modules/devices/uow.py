from sqlalchemy.ext.asyncio import AsyncSession

from backend_engine.modules.audit.writer import SqlAlchemyAuditWriter
from backend_engine.modules.devices.repository import SqlAlchemyDeviceRepository
from backend_engine.shared.storage.uow import BaseUnitOfWork


class DevicesUnitOfWork(BaseUnitOfWork):
    devices: SqlAlchemyDeviceRepository
    audit: SqlAlchemyAuditWriter

    def _bind(self, session: AsyncSession) -> None:
        self.devices = SqlAlchemyDeviceRepository(session)
        self.audit = SqlAlchemyAuditWriter(session)
