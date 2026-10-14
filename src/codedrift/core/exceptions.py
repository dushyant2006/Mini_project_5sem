"""
Domain exception hierarchy for CodeDrift.
"""


class CodeDriftError(Exception):
    """Base exception for all CodeDrift operations."""
    pass


class ParsingError(CodeDriftError):
    """Raised when AST parsing fails or file syntax is invalid."""
    pass


class DiffEngineError(CodeDriftError):
    """Raised when comparing two module representations fails."""
    pass


class CallGraphError(CodeDriftError):
    """Raised when constructing static call graphs or resolving symbols fails."""
    pass


class PolicyGateViolation(CodeDriftError):
    """Raised when a CI/CD build fails the breaking change policy."""
    def __init__(self, message: str, exit_code: int = 1, violations: list = None):
        super().__init__(message)
        self.exit_code = exit_code
        self.violations = violations or []
