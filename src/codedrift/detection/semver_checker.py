"""
SemVer Compatibility Auditor.
Validates whether detected API changes conform to Semantic Versioning (SemVer 2.0.0) rules.
"""
from typing import Dict, List, Optional
import re
from ..core.models import DiffResult, APIChange


class SemVerAuditor:
    """
    Audits an upstream version upgrade against detected API changes to detect
    undocumented or illegal breaking changes in MINOR or PATCH releases.
    """

    @staticmethod
    def parse_semver(version_str: str) -> Optional[Dict[str, int]]:
        pattern = r"^v?(\d+)\.(\d+)\.(\d+)"
        match = re.match(pattern, version_str.strip())
        if not match:
            return None
        return {
            "major": int(match.group(1)),
            "minor": int(match.group(2)),
            "patch": int(match.group(3)),
        }

    def audit_bump(
        self,
        old_version: str,
        new_version: str,
        diff_result: DiffResult,
    ) -> Dict[str, any]:
        old_v = self.parse_semver(old_version)
        new_v = self.parse_semver(new_version)

        has_breaking = len(diff_result.breaking_changes) > 0
        has_additions = any(c.change_type in ("FUNCTION_ADDED", "CLASS_ADDED", "METHOD_ADDED", "PARAMETER_ADDED") for c in diff_result.changes)

        if not old_v or not new_v:
            return {
                "valid": True,
                "reason": "Non-standard SemVer string provided, skipped strict SemVer audit.",
                "bump_type": "UNKNOWN",
                "semver_violation": False,
            }

        bump_type = "PATCH"
        if new_v["major"] > old_v["major"]:
            bump_type = "MAJOR"
        elif new_v["minor"] > old_v["minor"]:
            bump_type = "MINOR"
        elif new_v["patch"] > old_v["patch"]:
            bump_type = "PATCH"

        violations: List[str] = []
        is_violation = False

        if has_breaking and bump_type != "MAJOR":
            is_violation = True
            violations.append(
                f"SemVer Violation: {len(diff_result.breaking_changes)} breaking changes detected, but version bumped as {bump_type} ({old_version} -> {new_version}). A MAJOR bump is required."
            )

        return {
            "valid": not is_violation,
            "bump_type": bump_type,
            "semver_violation": is_violation,
            "violations": violations,
            "breaking_count": len(diff_result.breaking_changes),
            "total_changes": len(diff_result.changes),
        }
