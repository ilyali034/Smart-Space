"""App settings. URL/poll/demo live in QSettings; the API token lives only in the
OS credential store (Windows Credential Manager via `keyring`)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol
from urllib.parse import urlparse

from PySide6.QtCore import QObject, QSettings, Signal

DEFAULT_BASE_URL = "http://localhost:8000"
POLL_CHOICES = (5, 10, 30, 60)
_KEYRING_SERVICE = "SmartSpaceDesktop"
_KEYRING_USER = "api_token"


@dataclass(frozen=True)
class Settings:
    base_url: str = DEFAULT_BASE_URL
    token: str | None = None
    poll_seconds: int = 10
    demo_mode: bool = False

    @property
    def has_token(self) -> bool:
        return bool(self.token)


def validate_base_url(text: str) -> bool:
    try:
        u = urlparse(text.strip())
        return u.scheme in ("http", "https") and bool(u.hostname)
    except ValueError:
        return False


class TokenStore(Protocol):
    def get(self) -> str | None: ...
    def set(self, token: str | None) -> None: ...


class MemoryTokenStore:
    def __init__(self, token: str | None = None) -> None:
        self._token = token

    def get(self) -> str | None:
        return self._token

    def set(self, token: str | None) -> None:
        self._token = token


class KeyringTokenStore:
    def get(self) -> str | None:
        try:
            import keyring

            return keyring.get_password(_KEYRING_SERVICE, _KEYRING_USER)
        except Exception:
            return None

    def set(self, token: str | None) -> None:
        import keyring

        if token:
            keyring.set_password(_KEYRING_SERVICE, _KEYRING_USER, token)
        else:
            try:
                keyring.delete_password(_KEYRING_SERVICE, _KEYRING_USER)
            except keyring.errors.PasswordDeleteError:
                pass


class SettingsStore(QObject):
    changed = Signal(object)  # emits Settings

    def __init__(self, qsettings: QSettings, tokens: TokenStore, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._q = qsettings
        self._tokens = tokens
        self._current = self._load()

    @property
    def current(self) -> Settings:
        return self._current

    def _load(self) -> Settings:
        try:
            poll = int(self._q.value("pollSeconds", 10))
        except (TypeError, ValueError):
            poll = 10
        return Settings(
            base_url=str(self._q.value("baseUrl", DEFAULT_BASE_URL)),
            token=self._tokens.get(),
            poll_seconds=max(3, poll),
            demo_mode=str(self._q.value("demoMode", "false")).lower() in ("true", "1"),
        )

    def save(self, new: Settings) -> None:
        token = (new.token or "").strip() or None
        normalized = replace(new, base_url=new.base_url.strip().rstrip("/"), token=token)
        self._q.setValue("baseUrl", normalized.base_url)
        self._q.setValue("pollSeconds", normalized.poll_seconds)
        self._q.setValue("demoMode", normalized.demo_mode)
        self._q.sync()
        self._tokens.set(normalized.token)
        self._current = normalized
        self.changed.emit(normalized)
