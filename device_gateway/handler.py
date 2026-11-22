"""Pure message handling (no MQTT inside), so it is easy to test."""

import json
import logging
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any
from uuid import UUID

from device_gateway.backend import BackendClient, Outcome

log = logging.getLogger(__name__)

_KINDS = ("status", "telemetry", "ack")
_NEGATIVE_TTL = 30.0  # seconds to remember "device unknown to backend"
_ACK_MEMORY = 2000


class GatewayHandler:
    def __init__(
        self,
        backend: BackendClient,
        *,
        topic_prefix: str,
        heartbeat_seconds: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._backend = backend
        self._prefix = topic_prefix.strip("/")
        self._heartbeat = heartbeat_seconds
        self._clock = clock
        self._slugs: dict[UUID, str] = {}
        self._unknown_until: dict[UUID, float] = {}
        self._last_sent: dict[UUID, tuple[dict[str, Any], float]] = {}
        self._acked: OrderedDict[UUID, None] = OrderedDict()  # QoS1 is at-least-once: dedupe

    @property
    def subscriptions(self) -> list[str]:
        return [f"{self._prefix}/+/{kind}" for kind in _KINDS]

    async def handle(self, topic: str, payload: bytes) -> None:
        try:
            await self._handle(topic, payload)
        except Exception:  # one bad message must never stop the gateway
            log.exception("failed to handle message on %s", topic)

    async def _handle(self, topic: str, payload: bytes) -> None:
        parsed = self._parse_topic(topic)
        if parsed is None:
            return
        device_id, kind = parsed
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            log.warning("dropping non-JSON payload on %s", topic)
            return
        if not isinstance(data, dict):
            log.warning("dropping non-object payload on %s", topic)
            return
        # The topic decides which device this is; a payload claiming another device is spoofed/buggy.
        claimed = data.get("device_id")
        if claimed is not None and str(claimed).lower() != str(device_id):
            log.warning("dropping message on %s: payload device_id %s differs from topic", topic, claimed)
            return

        if kind == "ack":
            await self._on_ack(device_id, data)
            return
        slug = await self._resolve(device_id)
        if slug is None:
            return
        if kind == "status":
            await self._on_status(device_id, slug, data)
        else:
            await self._on_telemetry(device_id, slug, data)

    def _parse_topic(self, topic: str) -> tuple[UUID, str] | None:
        head = self._prefix + "/"
        if not topic.startswith(head):
            return None
        parts = topic[len(head):].split("/")
        if len(parts) != 2 or parts[1] not in _KINDS:
            return None
        try:
            return UUID(parts[0]), parts[1]
        except ValueError:
            return None

    async def _resolve(self, device_id: UUID) -> str | None:
        if device_id in self._slugs:
            return self._slugs[device_id]
        if self._unknown_until.get(device_id, 0.0) > self._clock():
            return None
        outcome, slug = await self._backend.slug_for(device_id)
        if slug is not None:
            self._slugs[device_id] = slug
            self._unknown_until.pop(device_id, None)
            return slug
        if outcome is Outcome.NOT_FOUND:
            log.warning("device %s is not registered in the backend; ignoring it for %ss", device_id, _NEGATIVE_TTL)
            self._unknown_until[device_id] = self._clock() + _NEGATIVE_TTL
        return None

    async def _forget(self, device_id: UUID) -> None:
        self._slugs.pop(device_id, None)
        self._last_sent.pop(device_id, None)

    async def _on_status(self, device_id: UUID, slug: str, data: dict[str, Any]) -> None:
        online = data.get("online")
        if not isinstance(online, bool):
            avail = data.get("availability")
            online = {"online": True, "offline": False}.get(avail) if isinstance(avail, str) else None
        if online is None:
            log.warning("status for %s has neither 'online' nor a valid 'availability'", slug)
            return
        outcome = await self._backend.report_availability(slug, online)
        if outcome is Outcome.NOT_FOUND:
            await self._forget(device_id)
        if not online:
            self._last_sent.pop(device_id, None)  # next telemetry after a comeback must go through

    async def _on_telemetry(self, device_id: UUID, slug: str, data: dict[str, Any]) -> None:
        readings = data.get("readings")
        if not isinstance(readings, dict) or not readings:
            log.warning("telemetry for %s has no readings", slug)
            return
        now = self._clock()
        last = self._last_sent.get(device_id)
        if last is not None and last[0] == readings and now - last[1] < self._heartbeat:
            return  # unchanged and recently reported
        outcome = await self._backend.report_state(slug, readings)
        if outcome is Outcome.OK:
            self._last_sent[device_id] = (readings, now)
        elif outcome is Outcome.NOT_FOUND:
            await self._forget(device_id)

    async def _on_ack(self, device_id: UUID, data: dict[str, Any]) -> None:
        raw_cmd, ok = data.get("command_id"), data.get("ok")
        try:
            command_id = UUID(str(raw_cmd))
        except ValueError:
            log.warning("ack from %s without a valid command_id", device_id)
            return
        if not isinstance(ok, bool):
            log.warning("ack for %s without boolean 'ok'", command_id)
            return
        if command_id in self._acked:
            log.info("duplicate ack for %s ignored", command_id)
            return
        outcome = await self._backend.ack(command_id, ok)
        if outcome is Outcome.UNAVAILABLE:
            log.error("could not deliver ack for %s: backend unavailable", command_id)
            return  # not remembered, so a redelivery can still succeed
        if outcome is Outcome.CONFLICT:
            log.info("ack for %s ignored by backend (command already final)", command_id)
        elif outcome is Outcome.NOT_FOUND:
            log.warning("ack for unknown command %s", command_id)
        self._acked[command_id] = None
        while len(self._acked) > _ACK_MEMORY:
            self._acked.popitem(last=False)
