from __future__ import annotations

from PySide6.QtCore import QObject, QThreadPool, Signal

from smart_space_desktop.core.api_client import ApiClient
from smart_space_desktop.core.connection import ConnectionMonitor
from smart_space_desktop.core.settings import Settings, SettingsStore


class AppContext(QObject):
    """Wires settings -> API client -> connection monitor. Rebuilds the client
    whenever Base URL or token changes."""

    refresh_requested = Signal()  # Ctrl+R / Refresh button; pages listen to it

    def __init__(self, store: SettingsStore, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self._client: ApiClient | None = None
        self.monitor = ConnectionMonitor(lambda: self.store.current, self.client, self)
        self.store.changed.connect(self._on_settings)

    @property
    def settings(self) -> Settings:
        return self.store.current

    def client(self) -> ApiClient:
        if self._client is None:
            s = self.store.current
            self._client = ApiClient(s.base_url, s.token)
        return self._client

    def start(self) -> None:
        self.monitor.restart()

    def refresh(self) -> None:
        self.refresh_requested.emit()
        self.monitor.check()

    def _on_settings(self, _: Settings) -> None:
        self._client = None  # old client is dropped (in-flight requests finish on it)
        self.monitor.restart()

    def shutdown(self) -> None:
        self.monitor.stop()
        QThreadPool.globalInstance().waitForDone(2000)
        if self._client is not None:
            self._client.close()
