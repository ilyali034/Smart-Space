from fastapi import APIRouter

from backend_engine.api.v1 import devices, health

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(devices.router)
