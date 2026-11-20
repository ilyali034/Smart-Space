"""Single error type for the app. `message` is user-facing (Russian);
`technical` is for the diagnostics block only. Never put tokens in either."""

from __future__ import annotations

import enum

import httpx


class ErrorKind(enum.Enum):
    NETWORK = "network"
    TIMEOUT = "timeout"
    BAD_URL = "bad_url"
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    VALIDATION = "validation"
    SERVER = "server"
    BAD_RESPONSE = "bad_response"
    UNKNOWN = "unknown"


class AppError(Exception):
    def __init__(
        self,
        kind: ErrorKind,
        message: str,
        *,
        status_code: int | None = None,
        technical: str | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.status_code = status_code
        self.technical = technical

    def __repr__(self) -> str:
        return f"AppError({self.kind.name}, {self.status_code}, {self.message!r})"

    @classmethod
    def from_exception(cls, exc: Exception, method: str, path: str) -> AppError:
        tech = f"{method} {path} → {type(exc).__name__}"
        if isinstance(exc, httpx.TimeoutException):
            return cls(ErrorKind.TIMEOUT, "The backend did not respond in time.", technical=tech)
        if isinstance(exc, (httpx.InvalidURL, httpx.UnsupportedProtocol)):
            return cls(
                ErrorKind.BAD_URL,
                "Invalid backend URL. Expected format: http://host:8000.",
                technical=tech,
            )
        if isinstance(exc, httpx.TransportError):
            return cls(
                ErrorKind.NETWORK,
                "The backend is unavailable. Check the URL and ensure that the server is running.",
                technical=tech,
            )
        return cls(ErrorKind.UNKNOWN, "Unknown network error.", technical=tech)

    @classmethod
    def from_response(cls, resp: httpx.Response, method: str, path: str) -> AppError:
        code = resp.status_code
        detail = _detail(resp)
        tech = f"{method} {path} → {code}" + (f": {detail}" if detail else "")

        def mk(kind: ErrorKind, msg: str) -> AppError:
            return cls(kind, msg, status_code=code, technical=tech)

        if code >= 500:
            return mk(
                ErrorKind.SERVER,
                f"Backend server error ({code}). The object state may have changed; refresh the data.",
            )
        table = {
            400: (ErrorKind.BAD_REQUEST, "Invalid request."),
            401: (
                ErrorKind.UNAUTHORIZED,
                "The token is missing, invalid, or expired. Check it in Settings.",
            ),
            403: (ErrorKind.FORBIDDEN, "You do not have permission to perform this action."),
            404: (ErrorKind.NOT_FOUND, "Object not found."),
            409: (ErrorKind.CONFLICT, "State conflict. Refresh the data and try again."),
            422: (ErrorKind.VALIDATION, "The backend rejected the request data."),
        }
        kind, msg = table.get(code, (ErrorKind.UNKNOWN, f"Unexpected backend response ({code})."))
        return mk(kind, msg)


def _detail(resp: httpx.Response) -> str | None:
    try:
        data = resp.json()
    except ValueError:
        return None
    if isinstance(data, dict) and isinstance(data.get("detail"), str):
        return data["detail"]
    return None
