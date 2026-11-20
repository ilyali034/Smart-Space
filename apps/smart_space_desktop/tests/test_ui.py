from smart_space_desktop.core.settings import Settings
from smart_space_desktop.ui.main_window import MainWindow
from smart_space_desktop.ui.pages.settings_page import SettingsPage


def test_starts_on_dashboard_and_shows_demo_marker(qtbot, demo_ctx):
    w = MainWindow(demo_ctx)
    qtbot.addWidget(w)
    w.show()
    assert w.current_key == "dashboard"
    assert w.sidebar.buttons["dashboard"].isChecked()
    assert w.topbar.title.text() == "Dashboard"
    assert w.topbar.demo_badge.isVisible()
    assert "DEMO MODE" in w.sidebar.info.text()
    assert w.minimumWidth() == 1100 and w.minimumHeight() == 700


def test_sidebar_click_navigates(qtbot, demo_ctx):
    w = MainWindow(demo_ctx)
    qtbot.addWidget(w)
    w.sidebar.buttons["devices"].click()
    assert w.current_key == "devices"
    assert w.stack.currentWidget() is w.pages["devices"]
    assert w.topbar.title.text() == "Devices"


def test_all_routes_reachable(qtbot, demo_ctx):
    w = MainWindow(demo_ctx)
    qtbot.addWidget(w)
    for key in w.pages:
        w.navigate(key, animate=False)
        assert w.stack.currentWidget() is w.pages[key]


def test_keyboard_shortcuts(qtbot, demo_ctx):
    w = MainWindow(demo_ctx)
    qtbot.addWidget(w)
    for seq, key in [("Ctrl+3", "devices"), ("Ctrl+2", "rooms"), ("Ctrl+4", "commands"),
                     ("Ctrl+,", "settings"), ("Ctrl+1", "dashboard")]:
        w.shortcuts[seq].activated.emit()
        assert w.current_key == key
    with qtbot.waitSignal(demo_ctx.refresh_requested, timeout=1000):
        w.shortcuts["Ctrl+R"].activated.emit()


def test_settings_rejects_bad_url_and_saves_good(qtbot, demo_ctx):
    w = MainWindow(demo_ctx)
    qtbot.addWidget(w)
    page: SettingsPage = w.pages["settings"]  # type: ignore[assignment]
    page.url.setText("localhost:8000")
    page.save(check=False)
    assert demo_ctx.settings.base_url != "localhost:8000"
    assert not page.url_error.isHidden()

    page.url.setText("http://10.0.0.5:8000/")
    page.token.setText("ss_tok")
    page.poll_buttons[30].setChecked(True)
    page.demo.setChecked(True)  # stay in demo: no network in tests
    page.save(check=False)
    s = demo_ctx.settings
    assert (s.base_url, s.token, s.poll_seconds) == ("http://10.0.0.5:8000", "ss_tok", 30)
    assert page.url_error.isHidden()


def test_leaving_demo_shows_real_status_then_marker_hidden(qtbot, store):
    from smart_space_desktop.core.context import AppContext
    from smart_space_desktop.core.connection import LinkState

    store.save(Settings(demo_mode=True))
    ctx = AppContext(store)
    w = MainWindow(ctx)
    qtbot.addWidget(w)
    w.show()
    assert w.topbar.demo_badge.isVisible()
    # unreachable port, no token: monitor must report a non-demo state
    with qtbot.waitSignal(ctx.monitor.changed, timeout=10000,
                          check_params_cb=lambda i: i.state not in (LinkState.DEMO, LinkState.CHECKING)):
        store.save(Settings(base_url="http://127.0.0.1:1", demo_mode=False))
    assert not w.topbar.demo_badge.isVisible()
    assert ctx.monitor.info.state is LinkState.UNREACHABLE
    assert "Offline" in w.topbar.chip.text()
    ctx.shutdown()
