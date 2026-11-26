from collections import Counter

from packaging.utils import canonicalize_name
from packaging.version import Version

from codedrift.dependency.package_comparator import (
    compare_package_versions,
    PackageComparisonError,
)

from codedrift.dependency.package_downloader import (
    PackageDownloadError,
)


DEFAULT_MAX_COMPARISONS = 5


def analyze_upgrades(
    dependencies,
    enabled=False,
    offline=False,
    max_comparisons=DEFAULT_MAX_COMPARISONS,
):

    if max_comparisons < 0:
        raise ValueError(
            "Comparison limit cannot be negative"
        )

    cache = {}

    results = []

    for dependency in dependencies:

        item = {
            **dependency,
            "api_analysis_status": "not_checked",
            "api_breaking_count": None,
            "api_comparison": None,
            "api_analysis_error": None,
        }

        baseline = dependency.get("baseline_version")

        candidate = dependency.get("latest_release")

        if offline:

            item["api_analysis_status"] = "offline"

        elif not enabled:

            item["api_analysis_status"] = "disabled"

        elif dependency["ecosystem"] != "pypi":

            item["api_analysis_status"] = (
                "unsupported_ecosystem"
            )

        elif baseline is None:

            item["api_analysis_status"] = (
                "unresolved_version"
            )

        elif dependency["comparison_status"] != (
            "update_available"
        ):

            item["api_analysis_status"] = (
                "no_update_available"
                if dependency["comparison_status"]
                == "up_to_date"
                else "update_not_confirmed"
            )

        elif candidate is None:

            item["api_analysis_status"] = (
                "candidate_unavailable"
            )

        else:

            key = (
                canonicalize_name(dependency["name"]),
                Version(baseline),
                Version(candidate),
            )

            if key not in cache:

                if len(cache) >= max_comparisons:

                    item["api_analysis_status"] = (
                        "comparison_limit_reached"
                    )

                    results.append(item)

                    continue

                try:

                    comparison = compare_package_versions(
                        dependency["name"],
                        baseline,
                        candidate,
                    )

                    status = comparison["comparison_status"]

                    cache[key] = {
                        "api_analysis_status": status,
                        "api_breaking_count": (
                            comparison["breaking_count"]
                            if status == "completed"
                            else None
                        ),
                        "api_comparison": comparison,
                        "api_analysis_error": (
                            comparison.get("reason")
                            if status != "completed"
                            else None
                        ),
                    }

                except (
                    PackageComparisonError,
                    PackageDownloadError,
                    OSError,
                    ValueError,
                ) as error:

                    cache[key] = {
                        "api_analysis_status": "failed",
                        "api_breaking_count": None,
                        "api_comparison": None,
                        "api_analysis_error": str(error),
                    }

            item.update(cache[key])

        results.append(item)

    statuses = Counter(
        item["api_analysis_status"]
        for item in results
    )

    completed = [
        item
        for item in cache.values()
        if item["api_analysis_status"] == "completed"
    ]

    return {
        "enabled": enabled,
        "offline": offline,
        "max_comparisons": max_comparisons,
        "unique_comparisons_attempted": len(cache),
        "unique_comparisons_completed": len(completed),
        "unique_comparisons_failed": sum(
            item["api_analysis_status"] == "failed"
            for item in cache.values()
        ),
        "unique_comparisons_incomplete": sum(
            item["api_analysis_status"] == "incomplete"
            for item in cache.values()
        ),
        "dependencies_with_breaking_changes": sum(
            (item["api_breaking_count"] or 0) > 0
            for item in results
        ),
        "unique_breaking_findings": sum(
            item["api_breaking_count"]
            for item in completed
        ),
        "status_distribution": dict(sorted(statuses.items())),
        "dependencies": results,
    }