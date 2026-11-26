import pytest

from unittest.mock import patch

from codedrift.dependency.upgrade_analyzer import (
    analyze_upgrades,
)

from codedrift.dependency.package_downloader import (
    PackageDownloadError,
)


COMPARATOR = (
    "codedrift.dependency.upgrade_analyzer."
    "compare_package_versions"
)


def make_dependency(
    name="flask",
    ecosystem="pypi",
    baseline="2.3.2",
    candidate="3.1.3",
    status="update_available",
):

    return {
        "name": name,
        "ecosystem": ecosystem,
        "baseline_version": baseline,
        "latest_release": candidate,
        "comparison_status": status,
    }


SAMPLE_COMPARISON = {
    "comparison_status": "completed",
    "total_changes": 3,
    "breaking_count": 2,
    "non_breaking_count": 1,
    "changes": [],
}


def test_upgrade_analysis():

    with patch(
        COMPARATOR,
        return_value=SAMPLE_COMPARISON,
    ) as comparator:

        report = analyze_upgrades(
            [make_dependency()],
            enabled=True,
        )

    comparator.assert_called_once_with(
        "flask",
        "2.3.2",
        "3.1.3",
    )

    assert report["unique_comparisons_completed"] == 1

    assert report["unique_breaking_findings"] == 2

    assert report["dependencies_with_breaking_changes"] == 1

    assert (
        report["dependencies"][0]["api_analysis_status"]
        == "completed"
    )


def test_disabled_analysis():

    with patch(COMPARATOR) as comparator:

        report = analyze_upgrades(
            [make_dependency()]
        )

    comparator.assert_not_called()

    assert (
        report["dependencies"][0]["api_analysis_status"]
        == "disabled"
    )


def test_offline_analysis():

    with patch(COMPARATOR) as comparator:

        report = analyze_upgrades(
            [make_dependency()],
            enabled=True,
            offline=True,
        )

    comparator.assert_not_called()

    assert (
        report["dependencies"][0]["api_analysis_status"]
        == "offline"
    )


def test_unsupported_ecosystem():

    with patch(COMPARATOR) as comparator:

        report = analyze_upgrades(
            [make_dependency(
                name="axios",
                ecosystem="npm",
            )],
            enabled=True,
        )

    comparator.assert_not_called()

    assert (
        report["dependencies"][0]["api_analysis_status"]
        == "unsupported_ecosystem"
    )


def test_unresolved_baseline():

    with patch(COMPARATOR) as comparator:

        report = analyze_upgrades(
            [make_dependency(baseline=None)],
            enabled=True,
        )

    comparator.assert_not_called()

    assert (
        report["dependencies"][0]["api_analysis_status"]
        == "unresolved_version"
    )


def test_up_to_date_dependency():

    with patch(COMPARATOR) as comparator:

        report = analyze_upgrades(
            [make_dependency(
                status="up_to_date",
                baseline="3.1.3",
            )],
            enabled=True,
        )

    comparator.assert_not_called()

    assert (
        report["dependencies"][0]["api_analysis_status"]
        == "no_update_available"
    )


def test_comparison_cache():

    dependencies = [
        make_dependency(),
        make_dependency(name="Flask"),
    ]

    with patch(
        COMPARATOR,
        return_value=SAMPLE_COMPARISON,
    ) as comparator:

        report = analyze_upgrades(
            dependencies,
            enabled=True,
        )

    comparator.assert_called_once()

    assert report["unique_comparisons_attempted"] == 1

    assert report["unique_breaking_findings"] == 2

    assert report["dependencies_with_breaking_changes"] == 2


def test_comparison_limit():

    dependencies = [
        make_dependency(),
        make_dependency(name="jinja2"),
    ]

    with patch(
        COMPARATOR,
        return_value=SAMPLE_COMPARISON,
    ) as comparator:

        report = analyze_upgrades(
            dependencies,
            enabled=True,
            max_comparisons=1,
        )

    comparator.assert_called_once()

    assert (
        report["dependencies"][1]["api_analysis_status"]
        == "comparison_limit_reached"
    )


def test_comparison_failure():

    with patch(
        COMPARATOR,
        side_effect=PackageDownloadError(
            "Download failed"
        ),
    ):

        report = analyze_upgrades(
            [make_dependency()],
            enabled=True,
        )

    assert report["unique_comparisons_failed"] == 1

    dependency = report["dependencies"][0]

    assert dependency["api_analysis_status"] == "failed"

    assert dependency["api_breaking_count"] is None

    assert dependency["api_analysis_error"] == (
        "Download failed"
    )


def test_incomplete_comparison():

    with patch(
        COMPARATOR,
        return_value={
            "comparison_status": "incomplete",
            "breaking_count": None,
            "reason": "Parsing failed",
        },
    ):

        report = analyze_upgrades(
            [make_dependency()],
            enabled=True,
        )

    assert report["unique_comparisons_incomplete"] == 1

    assert (
        report["dependencies"][0]["api_breaking_count"]
        is None
    )


def test_negative_comparison_limit():

    with pytest.raises(ValueError):

        analyze_upgrades(
            [make_dependency()],
            enabled=True,
            max_comparisons=-1,
        )