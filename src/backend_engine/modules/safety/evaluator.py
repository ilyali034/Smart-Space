from backend_engine.modules.safety.evaluate import Decision, Rule, evaluate as evaluate_decision
from backend_engine.modules.safety.policy import DEFAULT_RULES
from backend_engine.modules.safety.types import CommandRequest, SafetyContext


def evaluate(request: CommandRequest, context: SafetyContext) -> Decision:
    return evaluate_with_rules(request, context, DEFAULT_RULES)


def evaluate_with_rules(
    request: CommandRequest,
    context: SafetyContext,
    rules: tuple[Rule, ...],
) -> Decision:
    return evaluate_decision(request, context, rules)
