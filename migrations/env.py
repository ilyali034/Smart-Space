import asyncio

from alembic import context
from sqlalchemy.engine import Connection

from backend_engine.modules.audit.entity import AuditLogEntity  # noqa: F401
from backend_engine.modules.devices.entity import DeviceEntity  # noqa: F401
from backend_engine.modules.commands.entity import CommandEntity, SystemStateEntity  # noqa: F401
from backend_engine.shared.auth.tokens import ApiTokenEntity  # noqa: F401
from backend_engine.shared.config import Settings
from backend_engine.shared.storage.database import Base, create_engine

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=Settings.from_env().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_engine(Settings.from_env())
    async with engine.connect() as connection:
        await connection.run_sync(_do_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
