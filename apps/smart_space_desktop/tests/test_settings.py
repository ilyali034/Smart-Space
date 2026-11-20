from PySide6.QtCore import QSettings

from smart_space_desktop.core.settings import (
    MemoryTokenStore,
    Settings,
    SettingsStore,
    validate_base_url,
)


def test_validate_base_url():
    assert validate_base_url("http://localhost:8000")
    assert validate_base_url(" https://example.com ")
    assert not validate_base_url("localhost:8000")
    assert not validate_base_url("ftp://x")
    assert not validate_base_url("http://")
    assert not validate_base_url("")


def test_save_normalizes_persists_and_keeps_token_out_of_qsettings(tmp_path):
    path = str(tmp_path / "s.ini")
    tokens = MemoryTokenStore()
    st = SettingsStore(QSettings(path, QSettings.Format.IniFormat), tokens)
    seen = []
    st.changed.connect(seen.append)
    st.save(Settings(base_url=" http://h:1/// ", token="  ss_abc  ", poll_seconds=30, demo_mode=True))
    assert st.current.base_url == "http://h:1"
    assert st.current.token == "ss_abc"
    assert tokens.get() == "ss_abc"
    assert len(seen) == 1
    assert "ss_abc" not in open(path, encoding="utf-8").read()

    st2 = SettingsStore(QSettings(path, QSettings.Format.IniFormat), tokens)
    assert st2.current == st.current


def test_empty_token_clears_store(store):
    store.save(Settings(token="ss_x"))
    store.save(Settings(token="   "))
    assert store.current.token is None
