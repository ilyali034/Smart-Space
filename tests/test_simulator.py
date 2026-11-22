"""Simulator logic, no broker needed."""

import pytest

from backend_engine.modules.safety.actions import ACTIONS
from device_simulator.config import SimConfig, fallback_id
from device_simulator.control import build_message, parse_pairs
from device_simulator.devices import FLEETS, ClimateSensor, SmartLight, SmartSwitch, build_fleet
from device_simulator.faults import Faults
from device_simulator.mqtt.topics import Topics


def test_every_backend_action_is_understood_by_matching_devices() -> None:
    """Drift guard: if Safety gains an action, the simulator must learn it too."""
    light = SmartLight("l", "smart_light", ("on_off", "brightness"))
    switch = SmartSwitch("s", "smart_relay", ("on_off",))
    ok_params = {"turn_on": {}, "turn_off": {}, "set_brightness": {"brightness": 40}}
    assert set(ACTIONS) == set(ok_params), "update ok_params and the simulator for the new action"
    for action, params in ok_params.items():
        assert light.apply_command(action, params), action
        assert switch.apply_command(action, params) == (ACTIONS[action].capability == "on_off"), action


def test_fleet_capabilities_match_what_backend_requires() -> None:
    for specs in FLEETS.values():
        for s in specs:
            for action, spec in ACTIONS.items():
                dev = s.build()
                supported = dev.apply_command(action, {"brightness": 10} if action == "set_brightness" else {})
                assert supported == (spec.capability in s.capabilities), (s.slug, action)


@pytest.mark.parametrize("bad", [{"brightness": 101}, {"brightness": -1}, {"brightness": "5"}, {"brightness": True},
                                 {"brightness": 5.5}, {}, {"brightness": 5, "x": 1}])
def test_light_rejects_invalid_brightness(bad) -> None:
    light = SmartLight("l", "smart_light", brightness=50)
    assert light.apply_command("set_brightness", bad) is False
    assert light.brightness == 50


def test_light_state_changes() -> None:
    light = SmartLight("l", "smart_light")
    assert light.state() == {"power": False, "brightness": 100}
    light.apply_command("turn_on", {})
    light.apply_command("set_brightness", {"brightness": 0})
    assert light.state() == {"power": True, "brightness": 0}
    assert light.apply_command("turn_on", {"x": 1}) is False  # same strictness as the backend
    assert light.apply_command("self_destruct", {}) is False


def test_sensor_drifts_and_set_state_is_validated() -> None:
    s = ClimateSensor("t", "temperature_sensor", temperature=20.0)
    before = s.state()
    for _ in range(50):
        s.tick(3.0)
    assert 10.0 <= s.humidity <= 95.0 and s.state() != before
    assert s.set_state({"temperature": 99999}) is False
    assert s.set_state({"temperature": 30, "humidity": 55}) is True
    assert s.state() == {"temperature": 30.0, "humidity": 55.0}
    assert s.apply_command("turn_on", {}) is False  # sensors are not controllable


def test_sensors_report_only_their_own_quantity() -> None:
    t = next(x for x in FLEETS["living_room"] if x.slug == "living_temp").build()
    h = next(x for x in FLEETS["living_room"] if x.slug == "living_humidity").build()
    assert set(t.state()) == {"temperature"} and set(h.state()) == {"humidity"}
    assert h.set_state({"temperature": 30}) is False and h.set_state({"humidity": 60}) is True


def test_faults_counters_and_precedence() -> None:
    f = Faults(drop_next=1, fail_next=2)
    assert [f.next_outcome() for _ in range(4)] == ["drop", "fail", "fail", "ok"]


def test_faults_update_validates() -> None:
    f = Faults()
    rejected = f.update({"ack_delay": 2, "fail_next": 3, "duplicate_ack": True, "bogus": 1,
                         "drop_next": -1, "ack_delay_x": 1})
    assert (f.ack_delay, f.fail_next, f.duplicate_ack, f.drop_next) == (2.0, 3, True, 0)
    assert sorted(rejected) == ["ack_delay_x", "bogus", "drop_next"]
    assert Faults().update({"ack_delay": 999, "fail_next": True, "duplicate_ack": "yes"}) == [
        "ack_delay", "fail_next", "duplicate_ack"]


def test_topics_match_backend_dispatcher_layout() -> None:
    t = Topics("/smart-space/devices/")
    assert t.commands("abc") == "smart-space/devices/abc/commands"
    assert t.control == "smart-space/devices/_sim/control"


def test_control_message_building() -> None:
    assert parse_pairs(["a=1", "b=true", "c=x", "d=1.5"]) == {"a": 1, "b": True, "c": "x", "d": 1.5}
    assert build_message("faults", "lamp", ["ack_delay=2"]) == {"device": "lamp", "op": "faults", "faults": {"ack_delay": 2}}
    assert build_message("set", "t", ["temperature=30"])["state"] == {"temperature": 30}
    assert build_message("offline", "*", []) == {"device": "*", "op": "offline"}
    with pytest.raises(SystemExit):
        parse_pairs(["oops"])


def test_unknown_fleet_and_config(monkeypatch) -> None:
    with pytest.raises(ValueError):
        build_fleet(["nope"])
    assert len(build_fleet(["living_room", "kitchen"])) == 7
    assert fallback_id("a") == fallback_id("a") != fallback_id("b")
    monkeypatch.setenv("SIM_API_URL", "http://x:8000/")
    monkeypatch.setenv("SIM_API_TOKEN", "ss_t")
    monkeypatch.setenv("SIM_FLEET", "kitchen, living_room")
    cfg = SimConfig.from_env()
    assert cfg.api_url == "http://x:8000" and cfg.can_provision and cfg.fleets == ("kitchen", "living_room")
