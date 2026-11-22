"""Thin, retrying HTTP client for the backend endpoints the gateway needs."""

import asyncio
import enum
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

import httpx

log = logging.getLogger(__name__)
API = "/api/v1"


class Outcome(enum.Enum):
    OK = "ok"
    NOT_FOUND = "not_found"  # 404: unknown device/command
    CONFLICT = "conflict"  # 409: e.g. command already in a final state
    REJECTED = "rejected"  # other 4xx (401/403 = bad gateway token, 422 = bad payload)
    UNAVAILABLE = "unavailable"  # network error / 5xx after all retries


class BackendClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        retries: int = 3,
        backoff: float = 0.5,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._retries = retries
        self._backoff = backoff
        self._sleep = sleep

    async def _call(self, method: str, path: str, json: Any = None) -> tuple[Outcome, httpx.Response | None]:
        resp: httpx.Response | None = None
        for attempt in range(self._retries):
            try:
                resp = await self._client.request(method, f"{API}{path}", json=json)
            except httpx.HTTPError as exc:
                log.warning("backend %s %s failed: %s", method, path, type(exc).__name__)
            else:
                if resp.status_code < 500:
                    break
                log.warning("backend %s %s -> %s", method, path, resp.status_code)
            if attempt + 1 < self._retries:
                await self._sleep(self._backoff * (2**attempt))
        else:
            return Outcome.UNAVAILABLE, None
        code = resp.status_code
        if code < 300:
            return Outcome.OK, resp
        if code == 404:
            return Outcome.NOT_FOUND, resp
        if code == 409:
            return Outcome.CONFLICT, resp
        if code in (401, 403):
            log.error("backend refused the gateway token (%s). Check GATEWAY_API_TOKEN / role.", code)
        return Outcome.REJECTED, resp

    async def slug_for(self, device_id: UUID) -> tuple[Outcome, str | None]:
        outcome, resp = await self._call("GET", f"/devices/{device_id}")
        if outcome is Outcome.OK and resp is not None:
            return outcome, str(resp.json()["slug"])
        return outcome, None

    async def report_availability(self, slug: str, online: bool) -> Outcome:
        body = {"availability": "online" if online else "offline"}
        return (await self._call("PUT", f"/devices/{slug}/availability", body))[0]

    async def report_state(self, slug: str, state: dict[str, Any]) -> Outcome:
        return (await self._call("PUT", f"/devices/{slug}/state", {"state": state}))[0]

    async def ack(self, command_id: UUID, ok: bool) -> Outcome:
        return (await self._call("POST", f"/commands/{command_id}/ack", {"ok": ok}))[0]
