
import json

import pytest

from unittest.mock import patch

from codedrift.guard.upgrade_policy import (
    UpgradePolicy,
    evaluate_upgrade_policy,
)

from codedrift.guard.ci_guard import (
    run_ci_guard,
    generate_markdown_report,
    save_reports,
    main,
)


def make_dependency(**overrides):

    dependency = {
        "name": "paymentlib",
        "ecosystem": "pypi",
        "baseline_version": "1.0.0",
        "latest_release": "1.0.0",
        "comparison_status": "up_to_date",
        "security_status": "no_known_vulnerabilities",
        "vulnerability_count": 0,
        "api_analysis_status": "no_update_available",
        "impact_score": None,
        "impact_report": None,
    }

    dependency.update(overrides)

    return dependency


def make_report(dependencies):

    return {
        "repository": "demo",
        "dependencies": dependencies,
    }


def test_default_policy():

    policy = UpgradePolicy()

    assert policy.maximum_impact_score == 75

    assert policy.block_known_vulnerabilities


def test_policy_loading(tmp_path):

    path = tmp_path / "policy.json"

    path.write_text(
        json.dumps({
            "maximum_impact_score": 50,
            "fail_on_warning": True,
        }),
        encoding="utf-8",
    )

    policy = UpgradePolicy.load(path)

    assert policy.maximum_impact_score == 50

    assert policy.fail_on_warning


def test_invalid_policy_threshold():

    with pytest.raises(ValueError):

        UpgradePolicy(
            maximum_impact_score=101
        )


def test_negative_policy_threshold():

    with pytest.raises(ValueError):

        UpgradePolicy(
            maximum_impact_score=-1
        )


def test_missing_policy(tmp_path):

    with pytest.raises(FileNotFoundError):

        UpgradePolicy.load(
            tmp_path / "missing.json"
        )


def test_invalid_policy_boolean():

    with pytest.raises(ValueError):

        UpgradePolicy(
            fail_on_warning="false"
        )


def test_passed_decision():

    result = evaluate_upgrade_policy(
        make_report([
            make_dependency()
        ])
    )

    assert result["decision"] == "PASSED"

    assert result["exit_code"] == 0


def test_vulnerability_block():

    dependency = make_dependency(
        vulnerability_count=2,
        security_status="vulnerable",
    )

    result = evaluate_upgrade_policy(
        make_report([dependency])
    )

    assert result["decision"] == "BLOCKED"

    assert result["exit_code"] == 1


def test_vulnerability_rule_disabled():

    dependency = make_dependency(
        vulnerability_count=2,
        security_status="vulnerable",
    )

    policy = UpgradePolicy(
        block_known_vulnerabilities=False
    )

    result = evaluate_upgrade_policy(
        make_report([dependency]),
        policy,
    )

    assert result["decision"] == "PASSED"


def test_high_impact_block():

    dependency = make_dependency(
        impact_score=90
    )

    result = evaluate_upgrade_policy(
        make_report([dependency])
    )

    assert result["decision"] == "BLOCKED"


def test_custom_impact_threshold():

    dependency = make_dependency(
        impact_score=60
    )

    policy = UpgradePolicy(
        maximum_impact_score=50
    )

    result = evaluate_upgrade_policy(
        make_report([dependency]),
        policy,
    )

    assert result["decision"] == "BLOCKED"


def test_threshold_boundary():

    dependency = make_dependency(
        impact_score=75
    )

    result = evaluate_upgrade_policy(
        make_report([dependency])
    )

    assert result["decision"] == "PASSED"


def test_direct_breaking_usage():

    dependency = make_dependency(
        impact_report={
            "findings": [
                {
                    "severity": "CRITICAL",
                    "classification": "direct_usage",
                }
            ]
        }
    )

    result = evaluate_upgrade_policy(
        make_report([dependency])
    )

    assert result["decision"] == "BLOCKED"


def test_potential_usage_not_direct_block():

    dependency = make_dependency(
        impact_report={
            "findings": [
                {
                    "severity": "HIGH",
                    "classification": "potential_impact",
                }
            ]
        }
    )

    result = evaluate_upgrade_policy(
        make_report([dependency])
    )

    assert result["decision"] == "PASSED"


def test_unresolved_version_warning():

    dependency = make_dependency(
        baseline_version=None
    )

    result = evaluate_upgrade_policy(
        make_report([dependency])
    )

    assert result["decision"] == "WARNING"

    assert result["exit_code"] == 0


def test_fail_on_warning():

    dependency = make_dependency(
        baseline_version=None
    )

    policy = UpgradePolicy(
        fail_on_warning=True
    )

    result = evaluate_upgrade_policy(
        make_report([dependency]),
        policy,
    )

    assert result["decision"] == "WARNING"

    assert result["exit_code"] == 1


def test_security_lookup_failure():

    dependency = make_dependency(
        security_status="lookup_failed"
    )

    result = evaluate_upgrade_policy(
        make_report([dependency])
    )

    assert result["decision"] == "WARNING"


def test_incomplete_api_analysis():

    dependency = make_dependency(
        comparison_status="update_available",
        api_analysis_status="comparison_limit_reached",
    )

    result = evaluate_upgrade_policy(
        make_report([dependency])
    )

    assert result["decision"] == "WARNING"


def test_limited_impact_coverage():

    dependency = make_dependency(
        comparison_status="update_available",
        api_analysis_status="completed",
        impact_analysis_status="completed",
        impact_report={
            "coverage_limited": True,
            "findings": [],
        },
    )

    result = evaluate_upgrade_policy(
        make_report([dependency])
    )

    assert result["decision"] == "WARNING"


def test_empty_repository():

    result = evaluate_upgrade_policy(
        make_report([])
    )

    assert result["decision"] == "WARNING"


def test_analysis_warning():

    report = make_report([
        make_dependency()
    ])

    report["warnings"] = [
        "Manifest could not be parsed."
    ]

    result = evaluate_upgrade_policy(report)

    assert result["decision"] == "WARNING"


def test_block_has_priority():

    dependency = make_dependency(
        baseline_version=None,
        vulnerability_count=1,
    )

    result = evaluate_upgrade_policy(
        make_report([dependency])
    )

    assert result["decision"] == "BLOCKED"

    assert result["warning_count"] > 0


def test_runtime_not_verified():

    result = evaluate_upgrade_policy(
        make_report([
            make_dependency()
        ])
    )

    assert not result[
        "runtime_compatibility_verified"
    ]

    assert not result[
        "safe_to_auto_merge"
    ]


def test_local_ci_guard(tmp_path):

    with patch(
        "codedrift.guard.ci_guard."
        "analyze_full_local_repository",
        return_value=make_report([
            make_dependency()
        ]),
    ):

        result = run_ci_guard(tmp_path)

    assert result["policy_result"][
        "decision"
    ] == "PASSED"


def test_github_ci_guard():

    with patch(
        "codedrift.guard.ci_guard."
        "analyze_full_github_repository",
        return_value=make_report([
            make_dependency()
        ]),
    ) as analyzer:

        result = run_ci_guard(
            "https://github.com/owner/demo",
            max_comparisons=3,
        )

    assert analyzer.call_args.kwargs[
        "max_comparisons"
    ] == 3

    assert result["policy_result"][
        "decision"
    ] == "PASSED"


def test_markdown_report():

    report = make_report([
        make_dependency()
    ])

    result = {
        "analysis_report": report,
        "policy_result": evaluate_upgrade_policy(
            report
        ),
    }

    markdown = generate_markdown_report(result)

    assert "CodeDrift CI/CD Report" in markdown

    assert "PASSED" in markdown


def test_report_generation(tmp_path):

    report = make_report([
        make_dependency()
    ])

    result = {
        "analysis_report": report,
        "policy_result": evaluate_upgrade_policy(
            report
        ),
    }

    save_reports(
        result,
        tmp_path,
    )

    assert (
        tmp_path / "codedrift-report.json"
    ).exists()

    assert (
        tmp_path / "codedrift-report.md"
    ).exists()


def test_cli_passed(tmp_path, monkeypatch):

    monkeypatch.setattr(
        "sys.argv",
        [
            "ci_guard",
            ".",
            "--output-dir",
            str(tmp_path),
        ],
    )

    with patch(
        "codedrift.guard.ci_guard."
        "analyze_full_local_repository",
        return_value=make_report([
            make_dependency()
        ]),
    ):

        assert main() == 0


def test_cli_blocked(tmp_path, monkeypatch):

    monkeypatch.setattr(
        "sys.argv",
        [
            "ci_guard",
            ".",
            "--output-dir",
            str(tmp_path),
        ],
    )

    with patch(
        "codedrift.guard.ci_guard."
        "analyze_full_local_repository",
        return_value=make_report([
            make_dependency(
                vulnerability_count=1
            )
        ]),
    ):

        assert main() == 1


def test_cli_analysis_failure(monkeypatch):

    monkeypatch.setattr(
        "sys.argv",
        ["ci_guard", "."],
    )

    with patch(
        "codedrift.guard.ci_guard."
        "analyze_full_local_repository",
        side_effect=RuntimeError(
            "Analysis failed"
        ),
    ):

        assert main() == 2
