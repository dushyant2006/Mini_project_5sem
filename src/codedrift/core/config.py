"""
Configuration and Policy Definitions for CodeDrift Quality Gates.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from .enums import Severity


@dataclass
class GuardPolicy:
    """
    Defines thresholds and rules for passing or failing CI/CD builds.
    """
    fail_on_severity: Severity = Severity.HIGH
    max_allowable_blast_radius: float = 0.0  # Fail if any reachable breaking change exists
    ignore_patterns: List[str] = field(default_factory=lambda: ["*_test.py", "test_*.py", "tests/*", "venv/*", ".git/*"])
    allow_deprecated_usage: bool = True
    fail_on_unreachable_breaking: bool = False  # If false, upstream breaks that aren't called pass CI!
    custom_severity_weights: Dict[str, float] = field(default_factory=lambda: {
        "CRITICAL": 1.0,
        "HIGH": 0.8,
        "MEDIUM": 0.5,
        "LOW": 0.2,
        "INFO": 0.05,
    })


@dataclass
class CodeDriftConfig:
    policy: GuardPolicy = field(default_factory=GuardPolicy)
    upstream_package_name: Optional[str] = None
    verbose: bool = False
    output_format: str = "rich"  # rich, json, sarif, markdown
