"""Connection status. Backend has no WebSocket and no /me, so the only liveness
signal is polling GET /health (no auth) and then GET /devices?limit=1 (auth check)."""

from __future__ import annotations

import enum
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from smart_space_desktop.core.api_client import API_PREFIX, ApiClient
from smart_space_desktop.core.errors import AppError, ErrorKind
from smart_space_desktop.core.settings import Settings


class LinkState(enum.Enum):
    CHECKING = "checking"
    ONLINE = "online"
    NO_TOKEN = "no_token"
    UNAUTHORIZED = "unauthorized"
    UNREACHABLE = "unreachable"
    DEMO = "demo"


@dataclass(frozen=True)
class ConnectionInfo:
    state: LinkState
    message: str | None = None
    technical: str | None = None
    checked_at: datetime | None = None
    latency_ms: int | None = None


def probe(client: ApiClient, has_token: bool) -> ConnectionInfo:
    """Blocking; run it off the UI thread."""
    start = time.perf_counter()

    def info(state: LinkState, msg: str, tech: str | None = None) -> ConnectionInfo:
        return ConnectionInfo(
            state, msg, tech, datetime.now(), int((time.perf_counter() - start) * 1000)
        )

    try:
        client.get(f"{API_PREFIX}/health")
        if not has_token:
            return info(LinkState.NO_TOKEN, "Backend is reachable, but no token is configured.")
        client.get(f"{API_PREFIX}/devices", params={"limit": 1})
        return info(LinkState.ONLINE, "Connection established.")
    except AppError as e:
        if e.kind is ErrorKind.UNAUTHORIZED:
            return info(LinkState.UNAUTHORIZED, e.message, e.technical)
        if e.kind is ErrorKind.FORBIDDEN:  # token valid, role lacks device:read
            return info(LinkState.ONLINE, e.message, e.technical)
        return info(LinkState.UNREACHABLE, e.message, e.technical)


class _Signals(QObject):
    done = Signal(int, object)


class _Task(QRunnable):
    def __init__(self, gen: int, fn: Callable[[], ConnectionInfo], signals: _Signals) -> None:
        super().__init__()
        self._gen, self._fn, self._signals = gen, fn, signals

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # never let a worker die silently
            result = ConnectionInfo(
                LinkState.UNREACHABLE, "Unexpected connection-check error.", repr(exc), datetime.now()
            )
        self._signals.done.emit(self._gen, result)


class ConnectionMonitor(QObject):
    changed = Signal(object)  # emits ConnectionInfo

    def __init__(
        self,
        get_settings: Callable[[], Settings],
        get_client: Callable[[], ApiClient],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._get_settings = get_settings
        self._get_client = get_client
        self._gen = 0
        self._signals = _Signals(self)
        self._signals.done.connect(self._on_done)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.check)
        self.info = ConnectionInfo(LinkState.CHECKING)

    def restart(self) -> None:
        s = self._get_settings()
        self._gen += 1
        self._timer.stop()
        if s.demo_mode:
            self._set(ConnectionInfo(LinkState.DEMO, "Demo Mode: data is not from the backend."))
            return
        self._set(ConnectionInfo(LinkState.CHECKING))
        self._timer.start(s.poll_seconds * 1000)
        self.check()

    def check(self) -> None:
        s = self._get_settings()
        if s.demo_mode:
            return
        self._gen += 1
        gen = self._gen
        client, has_token = self._get_client(), s.has_token
        QThreadPool.globalInstance().start(_Task(gen, lambda: probe(client, has_token), self._signals))

    def stop(self) -> None:
        self._timer.stop()
        self._gen += 1

    def _on_done(self, gen: int, info: ConnectionInfo) -> None:
        if gen == self._gen:  # ignore stale results
            self._set(info)

    def _set(self, info: ConnectionInfo) -> None:
        self.info = info
        self.changed.emit(info)
