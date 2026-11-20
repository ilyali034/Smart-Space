import httpx

from smart_space_desktop.core.api_client import ApiClient
from smart_space_desktop.core.connection import ConnectionMonitor, LinkState, probe
from smart_space_desktop.core.settings import Settings


def mk(handler, token="ss_t"):
    return ApiClient("http://test", token, transport=httpx.MockTransport(handler))


def ok_handler(r):
    return httpx.Response(200, json={"status": "ok"} if r.url.path.endswith("health") else [])


def test_probe_online():
    assert probe(mk(ok_handler), True).state is LinkState.ONLINE


def test_probe_no_token_only_hits_health():
    paths = []

    def h(r):
        paths.append(r.url.path)
        return httpx.Response(200, json={"status": "ok"})

    assert probe(mk(h, None), False).state is LinkState.NO_TOKEN
    assert paths == ["/api/v1/health"]


def test_probe_unauthorized_forbidden_unreachable():
    def h401(r):
        return httpx.Response(200, json={}) if r.url.path.endswith("health") else httpx.Response(401)

    def h403(r):
        return httpx.Response(200, json={}) if r.url.path.endswith("health") else httpx.Response(403)

    def h503(r):
        return httpx.Response(503, json={"detail": "database unavailable"})

    assert probe(mk(h401), True).state is LinkState.UNAUTHORIZED
    assert probe(mk(h403), True).state is LinkState.ONLINE
    info = probe(mk(h503), True)
    assert info.state is LinkState.UNREACHABLE
    assert "database unavailable" in info.technical


def test_monitor_delivers_result_from_worker(qtbot):
    settings = Settings(token="ss_t", poll_seconds=60)
    client = mk(ok_handler)
    mon = ConnectionMonitor(lambda: settings, lambda: client)
    with qtbot.waitSignal(mon.changed, timeout=5000, check_params_cb=lambda i: i.state is LinkState.ONLINE):
        mon.restart()
    mon.stop()


def test_monitor_demo_makes_no_requests(qtbot):
    calls = []

    def h(r):
        calls.append(r)
        return httpx.Response(200)

    mon = ConnectionMonitor(lambda: Settings(demo_mode=True), lambda: mk(h))
    mon.restart()
    mon.check()
    assert mon.info.state is LinkState.DEMO
    assert calls == []
