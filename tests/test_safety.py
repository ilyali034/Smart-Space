import pytest

from backend_engine.modules.safety.evaluate import Verdict
from backend_engine.modules.safety.policy import DEFAULT_RULES
from backend_engine.modules.safety.evaluate import evaluate
from backend_engine.modules.safety.types import CommandRequest, CommandSource, SafetyContext


def ctx(**changes: object) -> SafetyContext:
    values = dict(device_exists=True, device_enabled=True, device_online=True,
                  device_type="smart_light", device_capabilities=("on_off", "brightness"),
                  emergency_stop=False, recent_command_count=0, rate_limit=100,
                  active_conflicting_commands=())
    values.update(changes)
    return SafetyContext(**values)


@pytest.mark.parametrize(("command_request", "context", "expected"), [
    (CommandRequest("bogus", {}, CommandSource.API), ctx(), Verdict.REJECT),
    (CommandRequest("turn_on", {}, CommandSource.API), ctx(device_capabilities=("brightness",)), Verdict.REJECT),
    (CommandRequest("set_brightness", {"brightness": 101}, CommandSource.API), ctx(), Verdict.REJECT),
    (CommandRequest("turn_on", {}, CommandSource.API), ctx(device_online=False), Verdict.REJECT),
    (CommandRequest("turn_on", {}, CommandSource.API), ctx(device_enabled=False), Verdict.REJECT),
    (CommandRequest("turn_on", {}, CommandSource.API), ctx(emergency_stop=True), Verdict.REJECT),
    (CommandRequest("turn_on", {}, CommandSource.API), ctx(recent_command_count=10, rate_limit=10), Verdict.REJECT),
])
def test_rejections(command_request: CommandRequest, context: SafetyContext, expected: Verdict) -> None:
    assert evaluate(command_request, context, DEFAULT_RULES).verdict == expected


def test_risky_relay_requires_confirmation() -> None:
    decision = evaluate(
        CommandRequest("turn_on", {}, CommandSource.API),
        ctx(device_type="smart_relay", device_capabilities=("on_off",)),
        DEFAULT_RULES,
    )
    assert decision.verdict == Verdict.CONFIRM


@pytest.mark.parametrize("source", [CommandSource.AI, CommandSource.AUTOMATION])
def test_ai_and_automation_cannot_confirm_risky_command(source: CommandSource) -> None:
    decision = evaluate(
        CommandRequest("turn_on", {}, source),
        ctx(device_type="smart_relay", device_capabilities=("on_off",)),
        DEFAULT_RULES,
    )
    assert decision.verdict == Verdict.REJECT
    assert "automated_confirmation_not_allowed" in decision.reasons


@pytest.mark.parametrize("parameters", [{"brightness": "50"}, {"brightness": 50.0}, {"brightness": -1}, {"brightness": 101}, {"extra": True}])
def test_invalid_brightness_parameters(parameters: dict[str, object]) -> None:
    decision = evaluate(
        CommandRequest("set_brightness", parameters, CommandSource.API),
        ctx(),
        DEFAULT_RULES,
    )
    assert decision.verdict == Verdict.REJECT
    assert "invalid_parameters" in decision.reasons


def test_conflict_rule_rejects_opposite_action() -> None:
    decision = evaluate(
        CommandRequest("turn_off", {}, CommandSource.API),
        ctx(active_conflicting_commands=("existing-command",)),
        DEFAULT_RULES,
    )
    assert decision.verdict == Verdict.REJECT
    assert "conflicting_command_active" in decision.reasons
