"""
Enumerations for CodeDrift API breaking change detection and governance.
"""
from enum import Enum, auto


class ChangeType(str, Enum):
    # Function & Method changes
    FUNCTION_REMOVED = "FUNCTION_REMOVED"
    FUNCTION_ADDED = "FUNCTION_ADDED"
    METHOD_REMOVED = "METHOD_REMOVED"
    METHOD_ADDED = "METHOD_ADDED"
    CLASS_REMOVED = "CLASS_REMOVED"
    CLASS_ADDED = "CLASS_ADDED"

    # Parameter changes
    PARAMETER_REMOVED = "PARAMETER_REMOVED"
    PARAMETER_ADDED_MANDATORY = "PARAMETER_ADDED_MANDATORY"
    PARAMETER_ADDED_OPTIONAL = "PARAMETER_ADDED_OPTIONAL"
    PARAMETER_REORDERED = "PARAMETER_REORDERED"
    PARAMETER_TYPE_CHANGED = "PARAMETER_TYPE_CHANGED"
    PARAMETER_DEFAULT_CHANGED = "PARAMETER_DEFAULT_CHANGED"

    # Contract & Behavioral changes
    RETURN_TYPE_CHANGED = "RETURN_TYPE_CHANGED"
    EXCEPTION_RAISED_CHANGED = "EXCEPTION_RAISED_CHANGED"
    DEPRECATION_ADDED = "DEPRECATION_ADDED"
    ASYNC_STATUS_CHANGED = "ASYNC_STATUS_CHANGED"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

    @property
    def weight(self) -> float:
        weights = {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.8,
            Severity.MEDIUM: 0.5,
            Severity.LOW: 0.2,
            Severity.INFO: 0.05,
        }
        return weights.get(self, 0.1)


class ParameterKind(str, Enum):
    POSITIONAL_ONLY = "POSITIONAL_ONLY"
    POSITIONAL_OR_KEYWORD = "POSITIONAL_OR_KEYWORD"
    KEYWORD_ONLY = "KEYWORD_ONLY"
    VAR_POSITIONAL = "VAR_POSITIONAL"
    VAR_KEYWORD = "VAR_KEYWORD"


class GateDecision(str, Enum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"
