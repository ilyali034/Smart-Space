from uuid import UUID

from fastapi import APIRouter, Depends, Request

from backend_engine.modules.commands.dto import AckCommandDto, CommandDto, SubmitCommandDto
from backend_engine.modules.commands.service import CommandService
from backend_engine.shared.auth.deps import get_principal
from backend_engine.shared.auth.principal import Principal

router = APIRouter(tags=["commands"])


def get_command_service(request: Request) -> CommandService:
    return request.app.state.command_service


@router.post("/devices/{slug}/command", response_model=CommandDto, status_code=201)
async def submit_command(
    slug: str,
    dto: SubmitCommandDto,
    actor: Principal = Depends(get_principal),
    service: CommandService = Depends(get_command_service),
) -> CommandDto:
    return await service.submit(actor, slug, dto)


@router.get("/commands/{command_id}", response_model=CommandDto)
async def get_command(
    command_id: UUID,
    actor: Principal = Depends(get_principal),
    service: CommandService = Depends(get_command_service),
) -> CommandDto:
    return await service.get(actor, command_id)


@router.post("/commands/{command_id}/confirm", response_model=CommandDto)
async def confirm_command(
    command_id: UUID,
    actor: Principal = Depends(get_principal),
    service: CommandService = Depends(get_command_service),
) -> CommandDto:
    return await service.confirm(actor, command_id)


@router.post("/commands/{command_id}/reject", response_model=CommandDto)
async def reject_command(
    command_id: UUID,
    actor: Principal = Depends(get_principal),
    service: CommandService = Depends(get_command_service),
) -> CommandDto:
    return await service.reject(actor, command_id)


@router.post("/commands/{command_id}/ack", response_model=CommandDto)
async def ack_command(
    command_id: UUID,
    dto: AckCommandDto,
    actor: Principal = Depends(get_principal),
    service: CommandService = Depends(get_command_service),
) -> CommandDto:
    return await service.on_ack(actor, command_id, dto.ok)


@router.post("/system/emergency-stop", status_code=204)
async def activate_emergency_stop(
    actor: Principal = Depends(get_principal),
    service: CommandService = Depends(get_command_service),
) -> None:
    await service.emergency_stop(actor)


@router.post("/system/emergency-stop/clear", status_code=204)
async def clear_emergency_stop(
    actor: Principal = Depends(get_principal),
    service: CommandService = Depends(get_command_service),
) -> None:
    await service.clear_emergency_stop(actor)
