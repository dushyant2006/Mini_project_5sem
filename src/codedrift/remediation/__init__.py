"""
CodeDrift Autonomous Remediation Subsystem.
"""
from .patch_generator import PatchGenerator
from .migration_guide import MigrationGuideSynthesizer
from ..core.models import RemediationPatch

__all__ = [
    "PatchGenerator",
    "MigrationGuideSynthesizer",
    "RemediationPatch",
]
