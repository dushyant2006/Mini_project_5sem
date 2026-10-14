"""
CI/CD Quality Gate Policy Engine for CodeDrift.
Evaluates blast-radius reports and diff results against configured governance policies.
"""
from typing import List, Optional
from ..core.config import GuardPolicy
from ..core.enums import GateDecision, Severity
from ..core.models import BlastRadiusReport, DiffResult, PolicyResult


class PolicyEngine:
    """
    Applies governance rules to determine whether a dependency upgrade is permitted.
    """

    def __init__(self, policy: Optional[GuardPolicy] = None):
        self.policy = policy or GuardPolicy()

    def evaluate(
        self,
        diff_result: DiffResult,
        blast_report: Optional[BlastRadiusReport] = None,
    ) -> PolicyResult:
        violations: List[str] = []

        # If blast_report is provided, base decision on reachable breaking changes
        if blast_report is not None:
            score = blast_report.blast_radius_score
            reachable_count = blast_report.reachable_breaking_count

            if score > self.policy.max_allowable_blast_radius:
                violations.append(
                    f"Blast Radius Violation: Score {score} exceeds maximum allowed threshold of {self.policy.max_allowable_blast_radius}."
                )

            if reachable_count > 0:
                violations.append(
                    f"Reachability Violation: {reachable_count} upstream breaking changes are actively invoked in client code."
                )

            if self.policy.fail_on_unreachable_breaking:
                unreachable = blast_report.total_breaking_upstream - reachable_count
                if unreachable > 0:
                    violations.append(
                        f"Strict Policy Violation: {unreachable} unreachable breaking changes detected in upstream package."
                    )

            if violations:
                return PolicyResult(
                    decision=GateDecision.BLOCKED,
                    exit_code=1,
                    summary=f"FAILED: Upgrade blocked due to {len(violations)} policy violation(s).",
                    violations=violations,
                    blast_radius_score=score,
                )
            else:
                return PolicyResult(
                    decision=GateDecision.PASSED,
                    exit_code=0,
                    summary="PASSED: Upgrade is compatible with client application.",
                    violations=[],
                    blast_radius_score=score,
                )

        # Fallback when no client codebase is analyzed (pure API diff mode)
        breaking = diff_result.breaking_changes
        if breaking:
            violations.append(f"Detected {len(breaking)} upstream breaking changes without client reachability audit.")
            return PolicyResult(
                decision=GateDecision.WARNING,
                exit_code=0,
                summary=f"WARNING: Upstream contains {len(breaking)} breaking changes.",
                violations=violations,
                blast_radius_score=0.0,
            )

        return PolicyResult(
            decision=GateDecision.PASSED,
            exit_code=0,
            summary="PASSED: Zero breaking changes detected.",
            violations=[],
            blast_radius_score=0.0,
        )
