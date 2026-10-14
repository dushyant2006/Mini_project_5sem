"""
Unit Tests for CI/CD Quality Gate Policy Evaluation.
"""
from codedrift.guard.policy_engine import PolicyEngine
from codedrift.core.config import GuardPolicy
from codedrift.core.enums import GateDecision
from codedrift.core.models import BlastRadiusReport, DiffResult, APIChange


def test_guard_blocks_when_reachable_breaking_changes_exist():
    policy = GuardPolicy(max_allowable_blast_radius=0.0)
    engine = PolicyEngine(policy)

    diff = DiffResult(changes=[APIChange("FN_REM", "lib.foo", is_breaking=True)])
    report = BlastRadiusReport(
        client_dir="src/client",
        total_breaking_upstream=1,
        reachable_breaking_count=1,
        blast_radius_score=45.0,
    )

    res = engine.evaluate(diff_result=diff, blast_report=report)
    assert res.decision == GateDecision.BLOCKED
    assert res.exit_code == 1
    assert len(res.violations) > 0


def test_guard_passes_when_blast_radius_is_zero():
    policy = GuardPolicy(max_allowable_blast_radius=0.0)
    engine = PolicyEngine(policy)

    diff = DiffResult(changes=[APIChange("FN_REM", "lib.foo", is_breaking=True)])
    report = BlastRadiusReport(
        client_dir="src/client",
        total_breaking_upstream=1,
        reachable_breaking_count=0,
        blast_radius_score=0.0,
    )

    res = engine.evaluate(diff_result=diff, blast_report=report)
    assert res.decision == GateDecision.PASSED
    assert res.exit_code == 0
    assert len(res.violations) == 0


def test_html_report_rendering():
    from codedrift.guard.reporter import DriftReporter
    diff = DiffResult(changes=[APIChange("FN_REM", "lib.foo", is_breaking=True, severity="CRITICAL")])
    reporter = DriftReporter()
    html = reporter.to_html(diff)
    assert "<!DOCTYPE html>" in html
    assert "CodeDrift Dependency Guard Report" in html
    assert "lib.foo" in html

