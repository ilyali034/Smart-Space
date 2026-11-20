"""The only place that talks HTTP. Everything else goes through this class."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from smart_space_desktop.core.errors import AppError, ErrorKind

API_PREFIX = "/api/v1"
log = logging.getLogger(__name__)


class ApiClient:
    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(
            base_url=base_url.strip().rstrip("/"),
            headers=headers,
            timeout=httpx.Timeout(10.0, connect=5.0),
            transport=transport,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> Any:
        try:
            resp = self._client.request(method, path, params=params, json=json_body)
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            # Log method/path/exception type only — never headers or bodies (token safety).
            log.warning("API %s %s failed: %s", method, path, type(exc).__name__)
            raise AppError.from_exception(exc, method, path) from exc
        if resp.status_code >= 400:
            log.warning("API %s %s -> %s", method, path, resp.status_code)
            raise AppError.from_response(resp, method, path)
        if resp.status_code == 204 or not resp.content:
            return None
        try:
            return resp.json()
        except ValueError as exc:
            raise AppError(
                ErrorKind.BAD_RESPONSE,
                "Backend returned an invalid response.",
                status_code=resp.status_code,
                technical=f"{method} {path} → invalid JSON",
            ) from exc

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, *, json_body: Any = None) -> Any:
        return self.request("POST", path, json_body=json_body)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)

    def close(self) -> None:
        self._client.close()
