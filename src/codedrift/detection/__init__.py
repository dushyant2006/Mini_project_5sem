"""
CodeDrift Breaking Change Detection Subsystem.
"""
from .diff_engine import DiffEngine
from .semver_checker import SemVerAuditor
from .models import APIChange, DiffResult

__all__ = [
    "DiffEngine",
    "SemVerAuditor",
    "APIChange",
    "DiffResult",
]