"""
Unified Domain Models for CodeDrift Core Architecture.
Includes AST representation, Diff classification, Call Graph, and Blast Radius entities.
"""
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from .enums import ChangeType, GateDecision, ParameterKind, Severity


@dataclass
class ParameterInfo:
    name: str
    kind: str = ParameterKind.POSITIONAL_OR_KEYWORD.value
    annotation: Optional[str] = None
    default: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FunctionInfo:
    name: str
    qualified_name: str
    signature: str
    parameters: List[ParameterInfo] = field(default_factory=list)
    return_type: Optional[str] = None
    visibility: str = "public"
    decorators: List[str] = field(default_factory=list)
    raises: List[str] = field(default_factory=list)
    is_async: bool = False
    docstring: Optional[str] = None
    line: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClassInfo:
    name: str
    qualified_name: str
    bases: List[str] = field(default_factory=list)
    visibility: str = "public"
    decorators: List[str] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)
    docstring: Optional[str] = None
    line: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImportInfo:
    module: str
    name: Optional[str] = None
    alias: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ModuleInfo:
    module_name: str
    file_path: str
    imports: List[ImportInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class APIChange:
    change_type: str
    qualified_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    parameter_name: Optional[str] = None
    severity: str = Severity.MEDIUM.value
    description: str = ""
    is_breaking: bool = True
    suggested_migration: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DiffResult:
    changes: List[APIChange] = field(default_factory=list)
    old_module_name: str = ""
    new_module_name: str = ""

    @property
    def breaking_changes(self) -> List[APIChange]:
        return [c for c in self.changes if c.is_breaking]

    @property
    def non_breaking_changes(self) -> List[APIChange]:
        return [c for c in self.changes if not c.is_breaking]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_changes": len(self.changes),
            "breaking_count": len(self.breaking_changes),
            "non_breaking_count": len(self.non_breaking_changes),
            "changes": [change.to_dict() for change in self.changes],
        }


@dataclass
class CallSite:
    file_path: str
    line: int
    column: int
    caller_function: Optional[str]
    callee_name: str
    matched_target: str
    code_snippet: str
    arguments_passed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BlastRadiusItem:
    change: APIChange
    call_sites: List[CallSite] = field(default_factory=list)
    is_reachable: bool = False
    impact_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change": self.change.to_dict(),
            "call_sites_count": len(self.call_sites),
            "call_sites": [cs.to_dict() for cs in self.call_sites],
            "is_reachable": self.is_reachable,
            "impact_score": self.impact_score,
        }


@dataclass
class BlastRadiusReport:
    client_dir: str
    total_breaking_upstream: int
    reachable_breaking_count: int
    blast_radius_score: float  # Normalized 0.0 to 100.0
    items: List[BlastRadiusItem] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_dir": self.client_dir,
            "total_breaking_upstream": self.total_breaking_upstream,
            "reachable_breaking_count": self.reachable_breaking_count,
            "blast_radius_score": round(self.blast_radius_score, 2),
            "affected_files": self.affected_files,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass
class RemediationPatch:
    file_path: str
    original_code: str
    patched_code: str
    diff: str
    target_symbol: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PolicyResult:
    decision: GateDecision
    exit_code: int
    summary: str
    violations: List[str] = field(default_factory=list)
    blast_radius_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "exit_code": self.exit_code,
            "summary": self.summary,
            "violations": self.violations,
            "blast_radius_score": self.blast_radius_score,
        }
