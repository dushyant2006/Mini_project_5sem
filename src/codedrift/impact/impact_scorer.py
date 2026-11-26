
import argparse
import json
import math

from collections import Counter
from pathlib import Path


SEVERITY_WEIGHTS = {
    "CRITICAL": 40.0,
    "HIGH": 25.0,
    "MEDIUM": 12.0,
    "LOW": 5.0,
    "INFO": 1.0,
}


CLASSIFICATION_WEIGHTS = {
    "direct_usage": 1.0,
    "potential_impact": 0.5,
}


def classify_risk(score):

    if score >= 75:
        return "CRITICAL"

    if score >= 50:
        return "HIGH"

    if score >= 25:
        return "MEDIUM"

    return "LOW"


def finding_identity(finding):

    return (
        finding["qualified_name"],
        finding["change_type"],
        finding.get("parameter_name"),
        finding["file_path"],
        finding["line"],
        finding.get("column", 0),
    )


def call_site_identity(finding):

    return (
        finding["file_path"],
        finding["line"],
        finding.get("column", 0),
    )


def calculate_finding_score(finding):

    severity = str(
        finding.get("severity", "MEDIUM")
    ).upper()

    classification = finding.get(
        "classification",
        "potential_impact",
    )

    severity_weight = SEVERITY_WEIGHTS.get(
        severity, 12.0
    )

    classification_weight = (
        CLASSIFICATION_WEIGHTS.get(
            classification, 0.0
        )
    )

    return round(
        severity_weight * classification_weight,
        2,
    )


def deduplicate_findings(findings):

    unique = {}

    for finding in findings:

        identity = finding_identity(finding)

        previous = unique.get(identity)

        if previous is None:

            unique[identity] = finding

        elif (
            calculate_finding_score(finding)
            > calculate_finding_score(previous)
        ):

            unique[identity] = finding

    return list(unique.values())


def calculate_impact_score(usage_report):

    if not isinstance(
        usage_report.get("findings"), list
    ):

        raise ValueError(
            "Usage report must contain individual findings."
        )

    findings = deduplicate_findings(
        usage_report["findings"]
    )

    findings = [
        finding
        for finding in findings
        if finding.get("classification")
        in CLASSIFICATION_WEIGHTS
    ]

    affected_files = set()

    affected_call_sites = set()

    affected_symbols = set()

    scored_findings = []

    site_scores = {}

    for finding in findings:

        score = calculate_finding_score(
            finding
        )

        site = call_site_identity(finding)

        affected_files.add(
            finding["file_path"]
        )

        affected_call_sites.add(site)

        affected_symbols.add(
            finding["qualified_name"]
        )

        site_scores[site] = max(
            site_scores.get(site, 0.0),
            score,
        )

        scored_findings.append({
            **finding,
            "finding_score": score,
        })

    raw_score = sum(
        site_scores.values()
    )

    impact_score = round(
        100 * (1 - math.exp(-raw_score / 40)),
        2,
    )

    severity_distribution = Counter(
        finding.get("severity", "MEDIUM")
        for finding in findings
    )

    classification_distribution = Counter(
        finding["classification"]
        for finding in findings
    )

    direct_count = (
        classification_distribution[
            "direct_usage"
        ]
    )

    potential_count = (
        classification_distribution[
            "potential_impact"
        ]
    )

    coverage_status = usage_report.get(
        "coverage_status",
        "unknown",
    )

    source_scan = usage_report.get(
        "source_scan", {}
    )

    resolver_warning_count = usage_report.get(
        "resolver_warning_count", 0
    )

    coverage_limited = (
        coverage_status != "supported_constructs_scanned"
        or not source_scan.get("complete", False)
        or resolver_warning_count > 0
    )

    if not findings:

        risk_level = "UNKNOWN"

        assessment = (
            "No affected API usage was detected. "
            "Compatibility has not been established."
        )

    else:

        risk_level = classify_risk(
            impact_score
        )

        assessment = (
            "Static API usage evidence indicates "
            "potential dependency upgrade impact."
        )

    if coverage_limited:

        assessment += (
            " Analysis coverage is limited; "
            "additional affected usage may exist."
        )

    scored_findings.sort(
        key=lambda finding: (
            -finding["finding_score"],
            finding["file_path"],
            finding["line"],
        )
    )

    return {
        "repository": usage_report.get(
            "repository"
        ),

        "package": usage_report.get(
            "package"
        ),

        "baseline_version": usage_report.get(
            "baseline_version"
        ),

        "candidate_version": usage_report.get(
            "candidate_version"
        ),

        "analysis_method": (
            "heuristic_static_impact_scoring"
        ),

        "impact_score": impact_score,

        "raw_score": round(raw_score, 2),

        "risk_level": risk_level,

        "assessment": assessment,

        "total_breaking_changes": usage_report.get(
            "total_breaking_changes", 0
        ),

        "total_findings": len(findings),

        "direct_usage_findings": direct_count,

        "potential_impact_findings": potential_count,

        "affected_file_count": len(
            affected_files
        ),

        "affected_call_site_count": len(
            affected_call_sites
        ),

        "affected_symbol_count": len(
            affected_symbols
        ),

        "affected_files": sorted(
            affected_files
        ),

        "affected_symbols": sorted(
            affected_symbols
        ),

        "severity_distribution": dict(
            sorted(severity_distribution.items())
        ),

        "classification_distribution": dict(
            sorted(
                classification_distribution.items()
            )
        ),

        "coverage_status": coverage_status,

        "coverage_limited": coverage_limited,

        "resolver_warning_count": (
            resolver_warning_count
        ),

        "runtime_compatibility_verified": False,

        "safe_to_auto_merge": False,

        "score_is_probability": False,

        "findings": scored_findings,
    }


def main():

    parser = argparse.ArgumentParser(
        description="CodeDrift impact scoring engine"
    )

    parser.add_argument(
        "usage_report",
        help="Breaking API usage JSON report",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
    )

    args = parser.parse_args()

    try:

        usage_report = json.loads(
            Path(args.usage_report).read_text(
                encoding="utf-8-sig"
            )
        )

        report = calculate_impact_score(
            usage_report
        )

        if args.summary:

            report.pop("findings")

        print(
            json.dumps(report, indent=2)
        )

        return 0

    except (OSError, ValueError) as error:

        parser.exit(
            status=1,
            message=f"CodeDrift error: {error}\n",
        )


if __name__ == "__main__":

    raise SystemExit(main())
