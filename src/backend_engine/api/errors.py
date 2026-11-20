from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend_engine.modules.devices.exceptions import (
    DeviceAlreadyExists,
    DeviceDisabled,
    DeviceNotFound,
)
from backend_engine.shared.auth.principal import Forbidden, Unauthenticated

_STATUS: dict[type[Exception], int] = {
    DeviceNotFound: 404,
    DeviceAlreadyExists: 409,
    DeviceDisabled: 409,
    Forbidden: 403,
    Unauthenticated: 401,
}


def _make_handler(status: int) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=status)

    return handler


def register_error_handlers(app: FastAPI) -> None:
    for exc_type, status in _STATUS.items():
        app.add_exception_handler(exc_type, _make_handler(status))
