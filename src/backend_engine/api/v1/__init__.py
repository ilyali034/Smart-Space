from fastapi import APIRouter

from backend_engine.api.v1 import commands, devices, health

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(devices.router)
router.include_router(commands.router)
