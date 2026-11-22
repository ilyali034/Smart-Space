from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from backend_engine.modules.devices.dto import (
    CreateDeviceDto,
    DeviceDto,
    ReportAvailabilityDto,
    ReportStateDto,
)
from backend_engine.modules.devices.service import DeviceService
from backend_engine.shared.auth.deps import get_principal
from backend_engine.shared.auth.principal import Principal

router = APIRouter(prefix="/devices", tags=["devices"])


def get_device_service(request: Request) -> DeviceService:
    service: DeviceService = request.app.state.device_service
    return service


@router.post("", response_model=DeviceDto, status_code=201)
async def create_device(
    dto: CreateDeviceDto,
    actor: Principal = Depends(get_principal),
    service: DeviceService = Depends(get_device_service),
) -> DeviceDto:
    return await service.create(actor, dto)


@router.get("", response_model=list[DeviceDto])
async def list_devices(
    room_id: UUID | None = None,
    type: str | None = None,
    availability: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    actor: Principal = Depends(get_principal),
    service: DeviceService = Depends(get_device_service),
) -> list[DeviceDto]:
    return await service.list_devices(
        actor, room_id=room_id, type_=type, availability=availability, limit=limit, offset=offset
    )


@router.get("/{device_id}", response_model=DeviceDto)
async def get_device(
    device_id: UUID,
    actor: Principal = Depends(get_principal),
    service: DeviceService = Depends(get_device_service),
) -> DeviceDto:
    return await service.get(actor, device_id)


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: UUID,
    actor: Principal = Depends(get_principal),
    service: DeviceService = Depends(get_device_service),
) -> Response:
    await service.delete(actor, device_id)
    return Response(status_code=204)


# ---- gateway-facing (role: gateway, permission device:report) ----


@router.put("/{slug}/availability", status_code=204)
async def report_availability(
    slug: str,
    dto: ReportAvailabilityDto,
    actor: Principal = Depends(get_principal),
    service: DeviceService = Depends(get_device_service),
) -> Response:
    await service.set_availability(actor, slug, dto.availability, seen_at=dto.seen_at)
    return Response(status_code=204)


@router.put("/{slug}/state", status_code=204)
async def report_state(
    slug: str,
    dto: ReportStateDto,
    actor: Principal = Depends(get_principal),
    service: DeviceService = Depends(get_device_service),
) -> Response:
    await service.report_state(actor, slug, dto.state, seen_at=dto.seen_at)
    return Response(status_code=204)

