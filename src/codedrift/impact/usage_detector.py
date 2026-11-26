
import argparse
import json

from collections import Counter, defaultdict
from pathlib import Path

from .symbol_resolver import resolve_repository


REMOVED_SYMBOL_TYPES = {
    "FUNCTION_REMOVED",
    "METHOD_REMOVED",
    "CLASS_REMOVED",
    "MODULE_REMOVED",
}


def matches_symbol(change, call):

    changed_symbol = change["qualified_name"]

    called_symbol = call["qualified_name"]

    change_type = change["change_type"]

    if changed_symbol == called_symbol:

        return True

    if change_type in {
        "MODULE_REMOVED",
        "CLASS_REMOVED",
    }:

        return called_symbol.startswith(
            changed_symbol + "."
        )

    return False


def classify_usage(change, call):

    change_type = change["change_type"]

    parameter = change.get("parameter_name")

    positional = call.get(
        "positional_arguments", []
    )

    keywords = call.get(
        "keyword_arguments", {}
    )

    starred = call.get(
        "has_starred_arguments", False
    )

    expanded = call.get(
        "has_expanded_keywords", False
    )

    if change_type in REMOVED_SYMBOL_TYPES:

        return (
            "direct_usage",
            "Application calls a symbol reported as removed.",
        )

    if change_type == "PARAMETER_REMOVED":

        if parameter in keywords:

            return (
                "direct_usage",
                f"Removed parameter '{parameter}' "
                "is explicitly supplied.",
            )

        if positional or starred or expanded:

            return (
                "potential_impact",
                f"Removed parameter '{parameter}' "
                "may be supplied through positional "
                "or expanded arguments.",
            )

        return (
            "no_argument_evidence",
            "No supplied argument matches "
            "the removed parameter.",
        )

    if change_type == "PARAMETER_ADDED_MANDATORY":

        return (
            "potential_impact",
            f"New mandatory parameter '{parameter}' "
            "requires signature compatibility review.",
        )

    if change_type == "PARAMETER_DEFAULT_CHANGED":

        if parameter in keywords:

            return (
                "no_argument_evidence",
                f"Parameter '{parameter}' "
                "is explicitly supplied.",
            )

        return (
            "potential_impact",
            f"Parameter '{parameter}' may depend "
            "on its previous default value.",
        )

    if change_type == "PARAMETER_REORDERED":

        if positional or starred:

            return (
                "potential_impact",
                "Positional arguments may bind "
                "to different parameters.",
            )

        return (
            "no_argument_evidence",
            "No positional arguments detected.",
        )

    if change_type == "PARAMETER_TYPE_CHANGED":

        if parameter in keywords:

            return (
                "potential_impact",
                f"Explicitly supplied parameter "
                f"'{parameter}' has a changed annotation.",
            )

        if positional or starred or expanded:

            return (
                "potential_impact",
                "Argument compatibility requires review.",
            )

        return (
            "no_argument_evidence",
            "No matching supplied argument detected.",
        )

    if change_type == "RETURN_TYPE_CHANGED":

        return (
            "potential_impact",
            "Return annotation changed. "
            "Downstream return-value usage requires review.",
        )

    if change_type == "ASYNC_STATUS_CHANGED":

        return (
            "potential_impact",
            "Synchronous or asynchronous "
            "calling behavior changed.",
        )

    if change_type == "VISIBILITY_REDUCED":

        return (
            "potential_impact",
            "Application uses an API with reduced visibility.",
        )

    if change_type == "INHERITANCE_CHANGED":

        return (
            "potential_impact",
            "Class inheritance changed. "
            "Behavior requires review.",
        )

    return (
        "potential_impact",
        "Application uses a changed API "
        "that requires compatibility review.",
    )


def create_finding(
    change,
    call,
    classification,
    reason,
):

    return {
        "change_type": change["change_type"],

        "qualified_name": change["qualified_name"],

        "called_symbol": call["qualified_name"],

        "parameter_name": change.get(
            "parameter_name"
        ),

        "severity": change.get(
            "severity", "MEDIUM"
        ),

        "classification": classification,

        "reason": reason,

        "file_path": call["file_path"],

        "line": call["line"],

        "column": call.get("column", 0),

        "caller_function": call.get(
            "caller_function"
        ),

        "callee_name": call.get(
            "callee_name"
        ),

        "code_snippet": call.get(
            "code_snippet", ""
        ),

        "positional_arguments": call.get(
            "positional_arguments", []
        ),

        "keyword_arguments": call.get(
            "keyword_arguments", {}
        ),

        "has_starred_arguments": call.get(
            "has_starred_arguments", False
        ),

        "has_expanded_keywords": call.get(
            "has_expanded_keywords", False
        ),

        "old_value": change.get("old_value"),

        "new_value": change.get("new_value"),

        "suggested_migration": change.get(
            "suggested_migration"
        ),
    }


def detect_breaking_usage(changes, calls):

    breaking_changes = [
        change
        for change in changes
        if change.get("is_breaking") is True
    ]

    calls_by_symbol = defaultdict(list)

    for call in calls:

        calls_by_symbol[
            call["qualified_name"]
        ].append(call)

    findings = []

    change_results = []

    affected_files = set()

    affected_call_sites = set()

    for change in breaking_changes:

        symbol = change["qualified_name"]

        change_type = change["change_type"]

        if change_type in {
            "MODULE_REMOVED",
            "CLASS_REMOVED",
        }:

            candidates = [
                call
                for call in calls
                if matches_symbol(change, call)
            ]

        else:

            candidates = calls_by_symbol.get(
                symbol, []
            )

        change_findings = []

        no_argument_evidence = 0

        for call in candidates:

            classification, reason = classify_usage(
                change,
                call,
            )

            if classification == "no_argument_evidence":

                no_argument_evidence += 1

                continue

            finding = create_finding(
                change,
                call,
                classification,
                reason,
            )

            findings.append(finding)

            change_findings.append(finding)

            affected_files.add(
                finding["file_path"]
            )

            affected_call_sites.add((
                finding["file_path"],
                finding["line"],
                finding["column"],
            ))

        if any(
            finding["classification"] == "direct_usage"
            for finding in change_findings
        ):

            status = "direct_usage"

        elif change_findings:

            status = "potential_impact"

        elif candidates:

            status = "no_argument_evidence"

        else:

            status = "no_usage_detected"

        change_results.append({
            "qualified_name": symbol,

            "change_type": change_type,

            "parameter_name": change.get(
                "parameter_name"
            ),

            "severity": change.get(
                "severity", "MEDIUM"
            ),

            "status": status,

            "matched_calls": len(candidates),

            "finding_count": len(
                change_findings
            ),

            "no_argument_evidence_count": (
                no_argument_evidence
            ),
        })

    findings.sort(
        key=lambda finding: (
            finding["file_path"],
            finding["line"],
            finding["column"],
            finding["qualified_name"],
            finding["change_type"],
            finding["parameter_name"] or "",
        )
    )

    classification_distribution = Counter(
        finding["classification"]
        for finding in findings
    )

    severity_distribution = Counter(
        finding["severity"]
        for finding in findings
    )

    change_status_distribution = Counter(
        result["status"]
        for result in change_results
    )

    return {
        "analysis_method": (
            "static_ast_breaking_usage_detection"
        ),

        "total_breaking_changes": len(
            breaking_changes
        ),

        "resolved_application_calls": len(calls),

        "changes_with_detected_usage": sum(
            result["finding_count"] > 0
            for result in change_results
        ),

        "changes_without_detected_usage": (
            change_status_distribution[
                "no_usage_detected"
            ]
        ),

        "total_findings": len(findings),

        "direct_usage_findings": (
            classification_distribution[
                "direct_usage"
            ]
        ),

        "potential_impact_findings": (
            classification_distribution[
                "potential_impact"
            ]
        ),

        "affected_file_count": len(
            affected_files
        ),

        "affected_call_site_count": len(
            affected_call_sites
        ),

        "affected_files": sorted(
            affected_files
        ),

        "severity_distribution": dict(
            sorted(severity_distribution.items())
        ),

        "classification_distribution": dict(
            sorted(
                classification_distribution.items()
            )
        ),

        "change_status_distribution": dict(
            sorted(
                change_status_distribution.items()
            )
        ),

        "change_results": change_results,

        "findings": findings,
    }


def analyze_repository_usage(
    repository_path,
    comparison_report,
):

    if comparison_report.get(
        "comparison_status"
    ) != "completed":

        raise ValueError(
            "Package comparison must be completed "
            "before usage analysis."
        )

    if not isinstance(
        comparison_report.get("changes"), list
    ):

        raise ValueError(
            "Comparison report must contain "
            "individual API changes."
        )

    changes = comparison_report["changes"]

    target_packages = sorted({
        change["qualified_name"].split(".")[0]
        for change in changes
        if change.get("is_breaking") is True
    })

    resolution = resolve_repository(
        repository_path,
        target_packages=target_packages,
    )

    report = detect_breaking_usage(
        changes,
        resolution["calls"],
    )

    source_complete = resolution[
        "source_scan"
    ]["complete"]

    warning_count = resolution[
        "warning_count"
    ]

    return {
        "repository": resolution["repository"],

        "package": comparison_report.get(
            "package"
        ),

        "baseline_version": comparison_report.get(
            "baseline_version"
        ),

        "candidate_version": comparison_report.get(
            "candidate_version"
        ),

        "target_import_packages": target_packages,

        "source_scan": resolution["source_scan"],

        "resolver_warning_count": warning_count,

        "resolver_warnings": resolution["warnings"],

        "coverage_status": (
            "limited"
            if not source_complete or warning_count
            else "supported_constructs_scanned"
        ),

        "runtime_compatibility_verified": False,

        **report,
    }


def main():

    parser = argparse.ArgumentParser(
        description=(
            "CodeDrift breaking API usage detector"
        )
    )

    parser.add_argument(
        "repository",
        help="Local application repository",
    )

    parser.add_argument(
        "comparison_report",
        help="Package comparison JSON file",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
    )

    args = parser.parse_args()

    try:

        comparison_report = json.loads(
            Path(args.comparison_report).read_text(
                encoding="utf-8-sig"
            )
        )

        report = analyze_repository_usage(
            args.repository,
            comparison_report,
        )

        if args.summary:

            report.pop("findings")

            report.pop("change_results")

            report.pop("resolver_warnings")

        print(json.dumps(report, indent=2))

        return 0

    except (OSError, ValueError) as error:

        parser.exit(
            status=1,
            message=f"CodeDrift error: {error}\n",
        )


if __name__ == "__main__":

    raise SystemExit(main())
