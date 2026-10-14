"""
CodeDrift Core Domain Layer: Enums, Models, Config, and Exceptions.
"""
from .enums import ChangeType, GateDecision, ParameterKind, Severity
from .models import (
    APIChange,
    BlastRadiusItem,
    BlastRadiusReport,
    CallSite,
    ClassInfo,
    DiffResult,
    FunctionInfo,
    ImportInfo,
    ModuleInfo,
    ParameterInfo,
    PolicyResult,
    RemediationPatch,
)
from .config import CodeDriftConfig, GuardPolicy
from .exceptions import (
    CallGraphError,
    CodeDriftError,
    DiffEngineError,
    ParsingError,
    PolicyGateViolation,
)

__all__ = [
    "ChangeType",
    "GateDecision",
    "ParameterKind",
    "Severity",
    "APIChange",
    "BlastRadiusItem",
    "BlastRadiusReport",
    "CallSite",
    "ClassInfo",
    "DiffResult",
    "FunctionInfo",
    "ImportInfo",
    "ModuleInfo",
    "ParameterInfo",
    "PolicyResult",
    "RemediationPatch",
    "CodeDriftConfig",
    "GuardPolicy",
    "CodeDriftError",
    "ParsingError",
    "DiffEngineError",
    "CallGraphError",
    "PolicyGateViolation",
]
