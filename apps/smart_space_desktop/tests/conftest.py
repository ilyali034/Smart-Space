import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings

from smart_space_desktop.core.context import AppContext
from smart_space_desktop.core.settings import MemoryTokenStore, Settings, SettingsStore


@pytest.fixture
def store(tmp_path):
    q = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    return SettingsStore(q, MemoryTokenStore())


@pytest.fixture
def demo_ctx(store):
    """Demo Mode => no HTTP and no polling timer in UI tests."""
    store.save(Settings(demo_mode=True))
    ctx = AppContext(store)
    yield ctx
    ctx.shutdown()
