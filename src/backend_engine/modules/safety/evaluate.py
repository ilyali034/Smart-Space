from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from backend_engine.modules.safety.types import CommandRequest, SafetyContext


class Verdict(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    CONFIRM = "confirm"


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    reasons: tuple[str, ...] = ()


class Rule(Protocol):
    def check(self, req: CommandRequest, ctx: SafetyContext) -> Decision | None: ...


def evaluate(req: CommandRequest, ctx: SafetyContext, rules: tuple[Rule, ...] | None = None) -> Decision:
    if rules is None:
        from backend_engine.modules.safety.policy import DEFAULT_RULES
        rules = DEFAULT_RULES
    confirms: list[str] = []
    for rule in rules:
        decision = rule.check(req, ctx)
        if decision is None:
            continue
        if decision.verdict == Verdict.REJECT:
            return decision
        if decision.verdict == Verdict.CONFIRM:
            confirms.extend(decision.reasons)
    if confirms:
        return Decision(Verdict.CONFIRM, tuple(dict.fromkeys(confirms)))
    return Decision(Verdict.APPROVE)
