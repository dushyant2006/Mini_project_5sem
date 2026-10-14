"""
CodeDrift: Autonomous API Breaking-Change & Dependency Degradation Guard.
"""
__version__ = "1.0.0"

from .core.models import (
    APIChange,
    DiffResult,
    BlastRadiusReport,
    PolicyResult,
    RemediationPatch,
)
from .core.enums import ChangeType, Severity, GateDecision
from .parser.python_parser import PythonParser
from .detection.diff_engine import DiffEngine
from .detection.semver_checker import SemVerAuditor
from .impact.blast_radius import BlastRadiusAnalyzer
from .impact.callgraph import CallGraphBuilder
from .guard.policy_engine import PolicyEngine
from .remediation.patch_generator import PatchGenerator
from .remediation.migration_guide import MigrationGuideSynthesizer

__all__ = [
    "__version__",
    "APIChange",
    "DiffResult",
    "BlastRadiusReport",
    "PolicyResult",
    "RemediationPatch",
    "ChangeType",
    "Severity",
    "GateDecision",
    "PythonParser",
    "DiffEngine",
    "SemVerAuditor",
    "BlastRadiusAnalyzer",
    "CallGraphBuilder",
    "PolicyEngine",
    "PatchGenerator",
    "MigrationGuideSynthesizer",
]
