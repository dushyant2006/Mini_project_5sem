
from unittest.mock import patch

from codedrift.repository.full_analyzer import (
    analyze_full_local_repository,
    analyze_full_github_repository,
    analyze_dependency_impact,
)


ANALYZER = (
    "codedrift.repository.full_analyzer."
    "analyze_local_repository"
)


def make_dependency():

    return {
        "name": "paymentlib",
        "ecosystem": "pypi",
        "baseline_version": "1.0.0",
        "latest_release": "2.0.0",
        "api_analysis_status": "completed",
        "api_comparison": {
            "comparison_status": "completed",
            "changes": [
                {
                    "qualified_name": "paymentlib.pay",
                    "change_type": "FUNCTION_REMOVED",
                    "severity": "CRITICAL",
                    "is_breaking": True,
                }
            ],
        },
    }


def make_repository_report(dependencies):

    return {
        "repository": "demo",
        "dependencies": dependencies,
    }


def test_full_repository_analysis(tmp_path):

    (tmp_path / "app.py").write_text(
        "import paymentlib\n"
        "paymentlib.pay(500)\n",
        encoding="utf-8",
    )

    with patch(
        ANALYZER,
        return_value=make_repository_report([
            make_dependency()
        ]),
    ):

        report = analyze_full_local_repository(
            tmp_path
        )

    impact = report["impact_analysis"]

    assert (
        impact["unique_impact_analyses_completed"]
        == 1
    )

    assert (
        impact["dependencies_with_detected_impact"]
        == 1
    )

    assert impact["affected_file_count"] == 1

    assert (
        impact["highest_dependency_impact_score"]
        > 0
    )


def test_no_application_usage(tmp_path):

    (tmp_path / "app.py").write_text(
        "print('Hello')\n",
        encoding="utf-8",
    )

    with patch(
        ANALYZER,
        return_value=make_repository_report([
            make_dependency()
        ]),
    ):

        report = analyze_full_local_repository(
            tmp_path
        )

    dependency = report["dependencies"][0]

    assert dependency["impact_score"] == 0

    assert dependency["risk_level"] == "UNKNOWN"


def test_comparison_unavailable():

    dependency = make_dependency()

    dependency["api_analysis_status"] = (
        "unresolved_version"
    )

    result = analyze_dependency_impact(
        dependency,
        {},
    )

    assert (
        result["impact_analysis_status"]
        == "comparison_unavailable"
    )

    assert result["impact_score"] is None


def test_duplicate_dependency_cache(tmp_path):

    (tmp_path / "app.py").write_text(
        "import paymentlib\n"
        "paymentlib.pay(500)\n",
        encoding="utf-8",
    )

    with patch(
        ANALYZER,
        return_value=make_repository_report([
            make_dependency(),
            make_dependency(),
        ]),
    ):

        report = analyze_full_local_repository(
            tmp_path
        )

    impact = report["impact_analysis"]

    assert len(report["dependencies"]) == 2

    assert (
        impact["unique_impact_analyses_completed"]
        == 1
    )

    assert impact["affected_call_site_count"] == 1


def test_offline_analysis(tmp_path):

    dependency = make_dependency()

    dependency["api_analysis_status"] = "offline"

    dependency["api_comparison"] = None

    with patch(
        ANALYZER,
        return_value=make_repository_report([
            dependency
        ]),
    ) as analyzer:

        report = analyze_full_local_repository(
            tmp_path,
            offline=True,
        )

    assert analyzer.call_args.kwargs["offline"]

    assert (
        report["impact_analysis"][
            "unique_impact_analyses_completed"
        ]
        == 0
    )


def test_empty_repository(tmp_path):

    with patch(
        ANALYZER,
        return_value=make_repository_report([]),
    ):

        report = analyze_full_local_repository(
            tmp_path
        )

    assert (
        report["impact_analysis"][
            "affected_file_count"
        ]
        == 0
    )

    assert (
        report["impact_analysis"][
            "highest_dependency_impact_score"
        ]
        is None
    )


def test_limited_coverage(tmp_path):

    (tmp_path / "app.py").write_text(
        "import paymentlib\n"
        "if condition:\n"
        "    paymentlib.pay(500)\n",
        encoding="utf-8",
    )

    with patch(
        ANALYZER,
        return_value=make_repository_report([
            make_dependency()
        ]),
    ):

        report = analyze_full_local_repository(
            tmp_path
        )

    assert report["impact_analysis"][
        "coverage_limited"
    ]

    assert not report["impact_analysis"][
        "safe_to_auto_merge"
    ]


def test_maximum_comparisons_forwarded(tmp_path):

    with patch(
        ANALYZER,
        return_value=make_repository_report([]),
    ) as analyzer:

        analyze_full_local_repository(
            tmp_path,
            max_comparisons=2,
        )

    assert (
        analyzer.call_args.kwargs[
            "max_comparisons"
        ]
        == 2
    )


def test_github_repository_analysis():

    paths = []

    def fake_clone(url, destination):

        destination.mkdir()

        (destination / "app.py").write_text(
            "import paymentlib\n"
            "paymentlib.pay(500)\n",
            encoding="utf-8",
        )

        paths.append(destination)

        return destination

    with patch(
        "codedrift.repository.full_analyzer."
        "clone_repository",
        side_effect=fake_clone,
    ):

        with patch(
            ANALYZER,
            return_value=make_repository_report([
                make_dependency()
            ]),
        ):

            report = analyze_full_github_repository(
                "https://github.com/owner/demo"
            )

    assert report["repository_url"] == (
        "https://github.com/owner/demo.git"
    )

    assert (
        report["impact_analysis"][
            "affected_file_count"
        ]
        == 1
    )

    assert not paths[0].exists()


def test_runtime_compatibility_not_verified(
    tmp_path,
):

    with patch(
        ANALYZER,
        return_value=make_repository_report([]),
    ):

        report = analyze_full_local_repository(
            tmp_path
        )

    assert not report["impact_analysis"][
        "runtime_compatibility_verified"
    ]
