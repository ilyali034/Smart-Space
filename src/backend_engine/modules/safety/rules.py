from pydantic import ValidationError

from backend_engine.modules.safety.actions import ACTIONS, Risk
from backend_engine.modules.safety.evaluate import Decision, Verdict
from backend_engine.modules.safety.types import CommandRequest, CommandSource, SafetyContext


class EmergencyStopRule:
    def check(self, req: CommandRequest, ctx: SafetyContext) -> Decision | None:
        if ctx.emergency_stop:
            return Decision(Verdict.REJECT, ("emergency_stop_active",))
        return None


class DeviceRule:
    def check(self, req: CommandRequest, ctx: SafetyContext) -> Decision | None:
        if not ctx.device_exists:
            return Decision(Verdict.REJECT, ("device_not_found",))
        if not ctx.device_enabled:
            return Decision(Verdict.REJECT, ("device_disabled",))
        if not ctx.device_online:
            return Decision(Verdict.REJECT, ("device_offline",))
        return None


class ActionAllowlistRule:
    def check(self, req: CommandRequest, ctx: SafetyContext) -> Decision | None:
        spec = ACTIONS.get(req.action)
        if spec is None:
            return Decision(Verdict.REJECT, ("unknown_action",))
        if spec.capability not in ctx.device_capabilities:
            return Decision(Verdict.REJECT, ("unsupported_action",))
        return None


class ParametersRule:
    def check(self, req: CommandRequest, ctx: SafetyContext) -> Decision | None:
        spec = ACTIONS.get(req.action)
        if spec is None:
            return None
        try:
            spec.params.model_validate(req.parameters)
        except ValidationError:
            return Decision(Verdict.REJECT, ("invalid_parameters",))
        return None


class RiskRule:
    def check(self, req: CommandRequest, ctx: SafetyContext) -> Decision | None:
        spec = ACTIONS.get(req.action)
        if spec is None:
            return None
        risky_device = ctx.device_type in {"smart_relay", "smart_plug"}
        if spec.risk == Risk.CONFIRM or (req.action == "turn_on" and risky_device):
            return Decision(Verdict.CONFIRM, ("risky_action",))
        return None


class SourceRule:
    def check(self, req: CommandRequest, ctx: SafetyContext) -> Decision | None:
        spec = ACTIONS.get(req.action)
        risky_device = ctx.device_type in {"smart_relay", "smart_plug"}
        risky_action = spec is not None and (spec.risk == Risk.CONFIRM or (req.action == "turn_on" and risky_device))
        if risky_action and req.source in {CommandSource.AI, CommandSource.AUTOMATION}:
            return Decision(Verdict.REJECT, ("automated_confirmation_not_allowed",))
        return None


class RateLimitRule:
    def check(self, req: CommandRequest, ctx: SafetyContext) -> Decision | None:
        if ctx.recent_command_count >= ctx.rate_limit:
            return Decision(Verdict.REJECT, ("rate_limit_exceeded",))
        return None


class ConflictRule:
    def check(self, req: CommandRequest, ctx: SafetyContext) -> Decision | None:
        if ctx.active_conflicting_commands:
            return Decision(Verdict.REJECT, ("conflicting_command_active",))
        return None
