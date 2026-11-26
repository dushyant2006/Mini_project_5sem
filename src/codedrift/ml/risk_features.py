
from packaging.version import Version, InvalidVersion


FEATURE_NAMES = [
    "major_upgrade",
    "minor_upgrade",
    "patch_upgrade",
    "breaking_count",
    "critical_count",
    "high_count",
    "direct_usage_count",
    "potential_usage_count",
    "affected_files",
    "coverage_limited",
]


def version_features(baseline, candidate):

    try:

        old = Version(str(baseline))
        new = Version(str(candidate))

        if new <= old:
            return 0, 0, 0

        major = int(new.major > old.major)

        minor = int(
            new.major == old.major
            and new.minor > old.minor
        )

        patch = int(
            new.major == old.major
            and new.minor == old.minor
            and new.micro > old.micro
        )

        return major, minor, patch

    except InvalidVersion:

        return 0, 0, 0


def extract_risk_features(dependency):

    if dependency.get("ecosystem") != "pypi":
        return None

    if dependency.get("comparison_status") != "update_available":
        return None

    if dependency.get("api_analysis_status") != "completed":
        return None

    if dependency.get("impact_analysis_status") != "completed":
        return None

    baseline = dependency.get("baseline_version")
    candidate = dependency.get("latest_release")

    if not baseline or not candidate:
        return None

    try:

        if Version(candidate) <= Version(baseline):
            return None

    except InvalidVersion:

        return None

    comparison = dependency.get("api_comparison") or {}
    impact = dependency.get("impact_report") or {}

    if dependency.get("api_breaking_count") is None:
        return None

    if not comparison or not impact:
        return None

    major, minor, patch = version_features(
        baseline,
        candidate,
    )

    changes = comparison.get("changes", [])

    breaking_changes = [
        change
        for change in changes
        if change.get("is_breaking") is True
    ]

    return {
        "major_upgrade": major,
        "minor_upgrade": minor,
        "patch_upgrade": patch,
        "breaking_count": dependency["api_breaking_count"],
        "critical_count": sum(
            str(change.get("severity")).upper() == "CRITICAL"
            for change in breaking_changes
        ),
        "high_count": sum(
            str(change.get("severity")).upper() == "HIGH"
            for change in breaking_changes
        ),
        "direct_usage_count": impact.get(
            "direct_usage_findings", 0
        ),
        "potential_usage_count": impact.get(
            "potential_impact_findings", 0
        ),
        "affected_files": impact.get(
            "affected_file_count", 0
        ),
        "coverage_limited": int(
            impact.get("coverage_limited", True)
        ),
    }


def feature_vector(features):

    return [
        float(features[name])
        for name in FEATURE_NAMES
    ]
