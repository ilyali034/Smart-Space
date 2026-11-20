import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend_engine.api.errors import register_error_handlers
from backend_engine.api.v1 import router as v1_router
from backend_engine.modules.devices.service import DeviceService
from backend_engine.modules.devices.uow import DevicesUnitOfWork
from backend_engine.shared.auth.tokens import TokenVerifier
from backend_engine.shared.config import Settings
from backend_engine.shared.events.bus import EventBus
from backend_engine.shared.storage.database import create_engine, create_session_factory

log = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Run with: uvicorn backend_engine.app:create_app --factory"""
    cfg = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(cfg)
        session_factory = create_session_factory(engine)
        bus = EventBus()

        app.state.engine = engine
        app.state.session_factory = session_factory
        app.state.bus = bus
        app.state.token_verifier = TokenVerifier(session_factory)
        app.state.device_service = DeviceService(
            lambda: DevicesUnitOfWork(session_factory, bus)
        )

        await bus.start()
        try:
            yield
        finally:
            await bus.stop()
            await engine.dispose()

    app = FastAPI(title="Smart Space", version="0.1.0", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(v1_router)
    return app
