from backend_engine.modules.safety.evaluate import Rule
from backend_engine.modules.safety.rules import (
    ActionAllowlistRule,
    ConflictRule,
    DeviceRule,
    EmergencyStopRule,
    ParametersRule,
    RateLimitRule,
    RiskRule,
    SourceRule,
)

DEFAULT_RULES: tuple[Rule, ...] = (
    EmergencyStopRule(),
    DeviceRule(),
    ActionAllowlistRule(),
    ParametersRule(),
    RiskRule(),
    SourceRule(),
    RateLimitRule(),
    ConflictRule(),
)
