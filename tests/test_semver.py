"""
Unit Tests for CodeDrift SemVer Compliance Auditor.
"""
from codedrift.detection.semver_checker import SemVerAuditor
from codedrift.core.models import DiffResult, APIChange


def test_semver_audit_detects_illegal_breaking_change_in_minor_bump():
    auditor = SemVerAuditor()
    diff = DiffResult(
        changes=[
            APIChange(
                change_type="FUNCTION_REMOVED",
                qualified_name="lib.foo",
                is_breaking=True,
                severity="CRITICAL",
            )
        ]
    )

    result = auditor.audit_bump("1.2.0", "1.3.0", diff)
    assert result["valid"] is False
    assert result["semver_violation"] is True
    assert result["bump_type"] == "MINOR"
    assert len(result["violations"]) == 1


def test_semver_audit_allows_breaking_change_in_major_bump():
    auditor = SemVerAuditor()
    diff = DiffResult(
        changes=[
            APIChange(
                change_type="FUNCTION_REMOVED",
                qualified_name="lib.foo",
                is_breaking=True,
                severity="CRITICAL",
            )
        ]
    )

    result = auditor.audit_bump("1.2.0", "2.0.0", diff)
    assert result["valid"] is True
    assert result["semver_violation"] is False
    assert result["bump_type"] == "MAJOR"
