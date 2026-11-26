
import pytest

from codedrift.impact.impact_scorer import (
    classify_risk,
    calculate_finding_score,
    calculate_impact_score,
    deduplicate_findings,
)


def make_finding(
    severity="HIGH",
    classification="direct_usage",
    symbol="paymentlib.pay",
    file_path="app.py",
    line=5,
    change_type="FUNCTION_REMOVED",
):

    return {
        "qualified_name": symbol,
        "change_type": change_type,
        "parameter_name": None,
        "severity": severity,
        "classification": classification,
        "file_path": file_path,
        "line": line,
        "column": 0,
    }


def make_report(findings):

    return {
        "repository": "demo",
        "package": "paymentlib",
        "baseline_version": "1.0.0",
        "candidate_version": "2.0.0",
        "total_breaking_changes": 3,
        "coverage_status": (
            "supported_constructs_scanned"
        ),
        "source_scan": {
            "complete": True,
        },
        "resolver_warning_count": 0,
        "findings": findings,
    }


def test_critical_finding_score():

    finding = make_finding(
        severity="CRITICAL"
    )

    assert calculate_finding_score(
        finding
    ) == 40.0


def test_high_finding_score():

    finding = make_finding(
        severity="HIGH"
    )

    assert calculate_finding_score(
        finding
    ) == 25.0


def test_potential_impact_weight():

    finding = make_finding(
        severity="HIGH",
        classification="potential_impact",
    )

    assert calculate_finding_score(
        finding
    ) == 12.5


def test_low_risk():

    assert classify_risk(10) == "LOW"


def test_medium_risk():

    assert classify_risk(25) == "MEDIUM"


def test_high_risk():

    assert classify_risk(50) == "HIGH"


def test_critical_risk():

    assert classify_risk(75) == "CRITICAL"


def test_empty_findings():

    report = calculate_impact_score(
        make_report([])
    )

    assert report["impact_score"] == 0

    assert report["risk_level"] == "UNKNOWN"

    assert not report["safe_to_auto_merge"]


def test_direct_usage_scoring():

    report = calculate_impact_score(
        make_report([
            make_finding()
        ])
    )

    assert report["impact_score"] > 0

    assert report["direct_usage_findings"] == 1


def test_potential_impact_scoring():

    report = calculate_impact_score(
        make_report([
            make_finding(
                classification="potential_impact"
            )
        ])
    )

    assert report["potential_impact_findings"] == 1


def test_direct_usage_has_higher_score():

    direct = calculate_impact_score(
        make_report([
            make_finding()
        ])
    )

    potential = calculate_impact_score(
        make_report([
            make_finding(
                classification="potential_impact"
            )
        ])
    )

    assert (
        direct["impact_score"]
        > potential["impact_score"]
    )


def test_duplicate_findings():

    finding = make_finding()

    result = deduplicate_findings([
        finding,
        finding,
    ])

    assert len(result) == 1


def test_duplicate_findings_not_double_counted():

    finding = make_finding()

    single = calculate_impact_score(
        make_report([finding])
    )

    duplicate = calculate_impact_score(
        make_report([finding, finding])
    )

    assert (
        single["impact_score"]
        == duplicate["impact_score"]
    )


def test_multiple_changes_same_call_site():

    findings = [
        make_finding(),

        make_finding(
            change_type="RETURN_TYPE_CHANGED"
        ),
    ]

    report = calculate_impact_score(
        make_report(findings)
    )

    assert report["total_findings"] == 2

    assert report["affected_call_site_count"] == 1

    assert report["raw_score"] == 25.0


def test_multiple_affected_files():

    report = calculate_impact_score(
        make_report([
            make_finding(file_path="app.py"),

            make_finding(file_path="payment.py"),
        ])
    )

    assert report["affected_file_count"] == 2

    assert report["affected_call_site_count"] == 2


def test_multiple_affected_symbols():

    report = calculate_impact_score(
        make_report([
            make_finding(symbol="paymentlib.pay"),

            make_finding(
                symbol="paymentlib.refund",
                line=10,
            ),
        ])
    )

    assert report["affected_symbol_count"] == 2


def test_score_upper_limit():

    findings = [
        make_finding(
            severity="CRITICAL",
            line=i,
        )
        for i in range(1, 101)
    ]

    report = calculate_impact_score(
        make_report(findings)
    )

    assert 0 <= report["impact_score"] <= 100


def test_limited_coverage():

    usage_report = make_report([
        make_finding()
    ])

    usage_report["coverage_status"] = "limited"

    usage_report["resolver_warning_count"] = 10

    report = calculate_impact_score(
        usage_report
    )

    assert report["coverage_limited"]

    assert report["resolver_warning_count"] == 10


def test_runtime_not_verified():

    report = calculate_impact_score(
        make_report([])
    )

    assert not report[
        "runtime_compatibility_verified"
    ]

    assert not report[
        "score_is_probability"
    ]


def test_invalid_usage_report():

    with pytest.raises(ValueError):

        calculate_impact_score({})
