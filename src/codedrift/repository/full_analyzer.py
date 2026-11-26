
import argparse
import json
import tempfile

from pathlib import Path
from collections import Counter

from packaging.utils import canonicalize_name

from .analyzer import analyze_local_repository

from .github_client import (
    clone_repository,
    validate_github_url,
    RepositoryError,
)

from codedrift.impact.usage_detector import (
    detect_breaking_usage,
)

from codedrift.impact.symbol_resolver import (
    resolve_repository,
)

from codedrift.impact.impact_scorer import (
    calculate_impact_score,
)


def analyze_dependency_impact(
    dependency,
    resolution,
):

    comparison = dependency.get(
        "api_comparison"
    )

    if (
        dependency.get("api_analysis_status")
        != "completed"
        or not comparison
        or comparison.get("comparison_status")
        != "completed"
    ):

        return {
            "impact_analysis_status": (
                "comparison_unavailable"
            ),
            "impact_score": None,
            "risk_level": "UNKNOWN",
            "impact_report": None,
        }

    changes = comparison.get("changes")

    if not isinstance(changes, list):

        return {
            "impact_analysis_status": (
                "comparison_details_missing"
            ),
            "impact_score": None,
            "risk_level": "UNKNOWN",
            "impact_report": None,
        }

    target_packages = {
        change["qualified_name"].split(".")[0]
        for change in changes
        if change.get("is_breaking") is True
    }

    relevant_calls = [
        call
        for call in resolution["calls"]
        if call["package"] in target_packages
    ]

    usage_report = detect_breaking_usage(
        changes,
        relevant_calls,
    )

    coverage_limited = (
        not resolution["source_scan"]["complete"]
        or resolution["warning_count"] > 0
    )

    usage_report.update({
        "repository": resolution["repository"],

        "package": dependency["name"],

        "baseline_version": dependency.get(
            "baseline_version"
        ),

        "candidate_version": dependency.get(
            "latest_release"
        ),

        "source_scan": resolution["source_scan"],

        "resolver_warning_count": (
            resolution["warning_count"]
        ),

        "coverage_status": (
            "limited"
            if coverage_limited
            else "supported_constructs_scanned"
        ),
    })

    impact = calculate_impact_score(
        usage_report
    )

    return {
        "impact_analysis_status": "completed",

        "impact_score": impact["impact_score"],

        "risk_level": impact["risk_level"],

        "impact_report": impact,
    }


def analyze_full_local_repository(
    repository_path,
    offline=False,
    max_comparisons=5,
):

    repository_path = Path(
        repository_path
    ).resolve()

    report = analyze_local_repository(
        repository_path,
        offline=offline,
        breaking_changes=True,
        max_comparisons=max_comparisons,
    )

    target_packages = set()

    for dependency in report["dependencies"]:

        comparison = dependency.get(
            "api_comparison"
        )

        if (
            comparison
            and comparison.get("comparison_status")
            == "completed"
        ):

            for change in comparison.get(
                "changes", []
            ):

                if change.get("is_breaking") is True:

                    target_packages.add(
                        change["qualified_name"]
                        .split(".")[0]
                    )

    resolution = resolve_repository(
        repository_path,
        target_packages=target_packages,
    )

    dependencies = []

    impact_cache = {}

    affected_files = set()

    affected_call_sites = set()

    for dependency in report["dependencies"]:

        cache_key = (
            dependency["ecosystem"],
            canonicalize_name(
                dependency["name"]
            ),
            dependency.get("baseline_version"),
            dependency.get("latest_release"),
            dependency.get("api_analysis_status"),
        )

        if cache_key not in impact_cache:

            impact_cache[cache_key] = (
                analyze_dependency_impact(
                    dependency,
                    resolution,
                )
            )

        impact = impact_cache[cache_key]

        item = {
            **dependency,
            **impact,
        }

        dependencies.append(item)

        impact_report = impact.get(
            "impact_report"
        )

        if impact_report:

            affected_files.update(
                impact_report["affected_files"]
            )

            for finding in impact_report[
                "findings"
            ]:

                affected_call_sites.add((
                    finding["file_path"],
                    finding["line"],
                    finding.get("column", 0),
                ))

    completed = [
        impact
        for impact in impact_cache.values()
        if impact["impact_analysis_status"]
        == "completed"
    ]

    risk_distribution = Counter(
        impact["risk_level"]
        for impact in impact_cache.values()
    )

    highest_score = max(
        (
            impact["impact_score"]
            for impact in completed
        ),
        default=None,
    )

    report["dependencies"] = dependencies

    report["impact_analysis"] = {

        "analysis_method": (
            "repository_static_impact_analysis"
        ),

        "unique_dependency_candidates": len(
            impact_cache
        ),

        "unique_impact_analyses_completed": len(
            completed
        ),

        "dependencies_with_detected_impact": sum(
            impact["impact_report"]["total_findings"] > 0
            for impact in completed
        ),

        "highest_dependency_impact_score": (
            highest_score
        ),

        "total_unique_impact_findings": sum(
            impact["impact_report"]["total_findings"]
            for impact in completed
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

        "risk_distribution": dict(
            sorted(risk_distribution.items())
        ),

        "source_scan": resolution["source_scan"],

        "resolved_application_calls": (
            resolution["resolved_calls"]
        ),

        "resolver_warning_count": (
            resolution["warning_count"]
        ),

        "coverage_limited": (
            not resolution["source_scan"]["complete"]
            or resolution["warning_count"] > 0
        ),

        "runtime_compatibility_verified": False,

        "safe_to_auto_merge": False,
    }

    return report


def analyze_full_github_repository(
    repository_url,
    offline=False,
    max_comparisons=5,
):

    safe_url = validate_github_url(
        repository_url
    )

    repository_name = (
        safe_url.rsplit("/", 1)[-1]
        .removesuffix(".git")
    )

    with tempfile.TemporaryDirectory(
        prefix="codedrift_full_",
        ignore_cleanup_errors=True,
    ) as workspace:

        destination = (
            Path(workspace) / repository_name
        )

        clone_repository(
            safe_url,
            destination,
        )

        report = analyze_full_local_repository(
            destination,
            offline=offline,
            max_comparisons=max_comparisons,
        )

        report["repository_url"] = safe_url

        return report


def main():

    parser = argparse.ArgumentParser(
        description=(
            "CodeDrift complete repository analyzer"
        )
    )

    parser.add_argument(
        "target",
        help="Local repository or GitHub URL",
    )

    parser.add_argument(
        "--offline",
        action="store_true",
    )

    parser.add_argument(
        "--max-comparisons",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--summary",
        action="store_true",
    )

    args = parser.parse_args()

    if args.max_comparisons < 0:

        parser.error(
            "Maximum comparisons cannot be negative."
        )

    try:

        if args.target.startswith("https://"):

            report = analyze_full_github_repository(
                args.target,
                offline=args.offline,
                max_comparisons=args.max_comparisons,
            )

        else:

            report = analyze_full_local_repository(
                args.target,
                offline=args.offline,
                max_comparisons=args.max_comparisons,
            )

        if args.summary:

            report.pop("dependencies", None)

        print(
            json.dumps(report, indent=2)
        )

        return 0

    except (
        RepositoryError,
        OSError,
        ValueError,
    ) as error:

        parser.exit(
            status=1,
            message=f"CodeDrift error: {error}\n",
        )


if __name__ == "__main__":

    raise SystemExit(main())
