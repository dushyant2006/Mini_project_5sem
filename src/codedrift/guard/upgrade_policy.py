
import json

from dataclasses import dataclass
from pathlib import Path


@dataclass
class UpgradePolicy:

    block_known_vulnerabilities: bool = True
    block_direct_high_severity: bool = True
    maximum_impact_score: float = 75.0
    warn_on_unresolved_versions: bool = True
    warn_on_incomplete_analysis: bool = True
    fail_on_warning: bool = False

    def __post_init__(self):

        if not 0 <= self.maximum_impact_score <= 100:
            raise ValueError(
                "Maximum impact score must be between 0 and 100."
            )

        for name in (
            "block_known_vulnerabilities",
            "block_direct_high_severity",
            "warn_on_unresolved_versions",
            "warn_on_incomplete_analysis",
            "fail_on_warning",
        ):

            if not isinstance(getattr(self, name), bool):
                raise ValueError(
                    f"{name} must be a boolean."
                )

    @classmethod
    def load(cls, file_path):

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Policy file not found: {path}"
            )

        data = json.loads(
            path.read_text(encoding="utf-8-sig")
        )

        if not isinstance(data, dict):
            raise ValueError(
                "Policy configuration must be a JSON object."
            )

        return cls(**data)


def create_violation(
    dependency,
    rule,
    message,
    level,
):

    return {
        "dependency": dependency.get("name"),
        "ecosystem": dependency.get("ecosystem"),
        "manifest": dependency.get("source_file"),
        "baseline_version": dependency.get(
            "baseline_version"
        ),
        "candidate_version": dependency.get(
            "latest_release"
        ),
        "rule": rule,
        "message": message,
        "level": level,
    }


def evaluate_upgrade_policy(report, policy=None):

    policy = policy or UpgradePolicy()

    violations = []

    dependencies = report.get("dependencies", [])

    for dependency in dependencies:

        name = dependency.get("name", "unknown")

        security_status = dependency.get(
            "security_status"
        )

        vulnerability_count = (
            dependency.get("vulnerability_count") or 0
        )

        if (
            policy.block_known_vulnerabilities
            and vulnerability_count > 0
        ):

            violations.append(
                create_violation(
                    dependency,
                    "KNOWN_VULNERABILITY",
                    f"{name} has known baseline vulnerabilities.",
                    "BLOCK",
                )
            )

        impact_score = dependency.get("impact_score")

        if (
            impact_score is not None
            and impact_score > policy.maximum_impact_score
        ):

            violations.append(
                create_violation(
                    dependency,
                    "IMPACT_THRESHOLD_EXCEEDED",
                    f"{name} impact score is {impact_score}.",
                    "BLOCK",
                )
            )

        impact_report = (
            dependency.get("impact_report") or {}
        )

        findings = impact_report.get("findings", [])

        if policy.block_direct_high_severity:

            direct_high_severity = [
                finding
                for finding in findings
                if (
                    finding.get("classification")
                    == "direct_usage"
                    and str(
                        finding.get("severity", "")
                    ).upper() in {"HIGH", "CRITICAL"}
                )
            ]

            if direct_high_severity:

                violations.append(
                    create_violation(
                        dependency,
                        "DIRECT_BREAKING_USAGE",
                        (
                            f"{name} has "
                            f"{len(direct_high_severity)} "
                            "high-severity direct usage findings."
                        ),
                        "BLOCK",
                    )
                )

        if (
            policy.warn_on_unresolved_versions
            and dependency.get("baseline_version") is None
        ):

            violations.append(
                create_violation(
                    dependency,
                    "UNRESOLVED_VERSION",
                    f"Baseline version of {name} is unresolved.",
                    "WARNING",
                )
            )

        if policy.warn_on_incomplete_analysis:

            if security_status not in {
                "vulnerable",
                "no_known_vulnerabilities",
            }:

                violations.append(
                    create_violation(
                        dependency,
                        "SECURITY_ANALYSIS_INCOMPLETE",
                        f"Security analysis of {name} is incomplete.",
                        "WARNING",
                    )
                )

            comparison_status = dependency.get(
                "comparison_status"
            )

            if comparison_status not in {
                "update_available",
                "up_to_date",
            }:

                violations.append(
                    create_violation(
                        dependency,
                        "VERSION_COMPARISON_INCOMPLETE",
                        f"Version comparison of {name} is incomplete.",
                        "WARNING",
                    )
                )

            if (
                comparison_status == "update_available"
                and dependency.get("api_analysis_status")
                != "completed"
            ):

                violations.append(
                    create_violation(
                        dependency,
                        "API_ANALYSIS_INCOMPLETE",
                        f"API analysis of {name} is incomplete.",
                        "WARNING",
                    )
                )

            elif comparison_status == "update_available":

                if (
                    dependency.get("impact_analysis_status")
                    != "completed"
                    or impact_report.get(
                        "coverage_limited", True
                    )
                ):

                    violations.append(
                        create_violation(
                            dependency,
                            "IMPACT_ANALYSIS_INCOMPLETE",
                            f"Impact analysis of {name} has limited coverage.",
                            "WARNING",
                        )
                    )

                if not impact_report.get(
                    "runtime_compatibility_verified", False
                ):

                    violations.append(
                        create_violation(
                            dependency,
                            "RUNTIME_NOT_VERIFIED",
                            f"Runtime compatibility of {name} is unverified.",
                            "WARNING",
                        )
                    )

    if policy.warn_on_incomplete_analysis:

        if not dependencies:

            violations.append(
                create_violation(
                    {},
                    "NO_DEPENDENCIES_ANALYZED",
                    "No dependency entries were analyzed.",
                    "WARNING",
                )
            )

        for warning in report.get("warnings", []):

            violations.append(
                create_violation(
                    {},
                    "ANALYSIS_WARNING",
                    str(warning),
                    "WARNING",
                )
            )

    blocking = [
        violation
        for violation in violations
        if violation["level"] == "BLOCK"
    ]

    warnings = [
        violation
        for violation in violations
        if violation["level"] == "WARNING"
    ]

    if blocking:

        decision = "BLOCKED"
        exit_code = 1

    elif warnings:

        decision = "WARNING"
        exit_code = 1 if policy.fail_on_warning else 0

    else:

        decision = "PASSED"
        exit_code = 0

    return {
        "repository": report.get("repository"),
        "decision": decision,
        "exit_code": exit_code,
        "dependency_count": len(dependencies),
        "blocking_violation_count": len(blocking),
        "warning_count": len(warnings),
        "violations": violations,
        "runtime_compatibility_verified": False,
        "safe_to_auto_merge": False,
    }
