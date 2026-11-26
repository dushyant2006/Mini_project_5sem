
import pytest

from codedrift.impact.usage_detector import (
    matches_symbol,
    classify_usage,
    detect_breaking_usage,
    analyze_repository_usage,
)


def make_change(
    change_type="FUNCTION_REMOVED",
    symbol="paymentlib.pay",
    parameter=None,
    breaking=True,
):

    return {
        "change_type": change_type,
        "qualified_name": symbol,
        "parameter_name": parameter,
        "severity": "HIGH",
        "is_breaking": breaking,
        "old_value": None,
        "new_value": None,
    }


def make_call(
    symbol="paymentlib.pay",
    positional=None,
    keywords=None,
    starred=False,
    expanded=False,
    file_path="app.py",
    line=3,
):

    return {
        "qualified_name": symbol,
        "package": symbol.split(".")[0],
        "file_path": file_path,
        "line": line,
        "column": 0,
        "caller_function": "checkout",
        "callee_name": symbol,
        "positional_arguments": positional or [],
        "keyword_arguments": keywords or {},
        "has_starred_arguments": starred,
        "has_expanded_keywords": expanded,
        "code_snippet": f"{symbol}()",
    }


def test_removed_function_usage():

    report = detect_breaking_usage(
        [make_change()],
        [make_call()],
    )

    assert report["total_findings"] == 1

    assert report["direct_usage_findings"] == 1

    assert report["affected_file_count"] == 1


def test_unrelated_function_not_matched():

    report = detect_breaking_usage(
        [make_change()],
        [make_call("otherlib.pay")],
    )

    assert report["total_findings"] == 0

    assert (
        report["changes_without_detected_usage"]
        == 1
    )


def test_removed_class_usage():

    change = make_change(
        "CLASS_REMOVED",
        "paymentlib.Client",
    )

    call = make_call(
        "paymentlib.Client"
    )

    assert matches_symbol(change, call)


def test_removed_class_method_usage():

    change = make_change(
        "CLASS_REMOVED",
        "paymentlib.Client",
    )

    call = make_call(
        "paymentlib.Client.connect"
    )

    assert matches_symbol(change, call)


def test_removed_module_usage():

    change = make_change(
        "MODULE_REMOVED",
        "paymentlib.utils",
    )

    call = make_call(
        "paymentlib.utils.convert"
    )

    assert matches_symbol(change, call)


def test_module_prefix_boundary():

    change = make_change(
        "MODULE_REMOVED",
        "paymentlib.utils",
    )

    call = make_call(
        "paymentlib.utils_extra.convert"
    )

    assert not matches_symbol(change, call)


def test_removed_keyword_parameter():

    change = make_change(
        "PARAMETER_REMOVED",
        parameter="currency",
    )

    call = make_call(
        keywords={"currency": "'INR'"}
    )

    classification, _ = classify_usage(
        change,
        call,
    )

    assert classification == "direct_usage"


def test_removed_positional_parameter():

    change = make_change(
        "PARAMETER_REMOVED",
        parameter="currency",
    )

    call = make_call(
        positional=["500", "'INR'"]
    )

    classification, _ = classify_usage(
        change,
        call,
    )

    assert classification == "potential_impact"


def test_removed_parameter_not_supplied():

    change = make_change(
        "PARAMETER_REMOVED",
        parameter="currency",
    )

    call = make_call(
        keywords={"amount": "500"}
    )

    classification, _ = classify_usage(
        change,
        call,
    )

    assert classification == "no_argument_evidence"


def test_expanded_keyword_arguments():

    change = make_change(
        "PARAMETER_REMOVED",
        parameter="currency",
    )

    call = make_call(
        expanded=True
    )

    classification, _ = classify_usage(
        change,
        call,
    )

    assert classification == "potential_impact"


def test_starred_arguments():

    change = make_change(
        "PARAMETER_REMOVED",
        parameter="currency",
    )

    call = make_call(
        starred=True
    )

    classification, _ = classify_usage(
        change,
        call,
    )

    assert classification == "potential_impact"


def test_mandatory_parameter_added():

    change = make_change(
        "PARAMETER_ADDED_MANDATORY",
        parameter="token",
    )

    classification, _ = classify_usage(
        change,
        make_call(),
    )

    assert classification == "potential_impact"


def test_default_removed():

    change = make_change(
        "PARAMETER_DEFAULT_CHANGED",
        parameter="timeout",
    )

    classification, _ = classify_usage(
        change,
        make_call(),
    )

    assert classification == "potential_impact"


def test_default_parameter_explicitly_supplied():

    change = make_change(
        "PARAMETER_DEFAULT_CHANGED",
        parameter="timeout",
    )

    call = make_call(
        keywords={"timeout": "10"}
    )

    classification, _ = classify_usage(
        change,
        call,
    )

    assert classification == "no_argument_evidence"


def test_parameter_reordering():

    change = make_change(
        "PARAMETER_REORDERED"
    )

    call = make_call(
        positional=["1", "2"]
    )

    classification, _ = classify_usage(
        change,
        call,
    )

    assert classification == "potential_impact"


def test_keyword_only_reordering():

    change = make_change(
        "PARAMETER_REORDERED"
    )

    call = make_call(
        keywords={"a": "1", "b": "2"}
    )

    classification, _ = classify_usage(
        change,
        call,
    )

    assert classification == "no_argument_evidence"


def test_return_annotation_change():

    change = make_change(
        "RETURN_TYPE_CHANGED"
    )

    classification, _ = classify_usage(
        change,
        make_call(),
    )

    assert classification == "potential_impact"


def test_non_breaking_change_ignored():

    change = make_change(
        "FUNCTION_ADDED",
        breaking=False,
    )

    report = detect_breaking_usage(
        [change],
        [make_call()],
    )

    assert report["total_breaking_changes"] == 0

    assert report["total_findings"] == 0


def test_unique_affected_call_sites():

    changes = [
        make_change(),
        make_change(
            "RETURN_TYPE_CHANGED"
        ),
    ]

    report = detect_breaking_usage(
        changes,
        [make_call()],
    )

    assert report["total_findings"] == 2

    assert report["affected_call_site_count"] == 1

    assert report["affected_file_count"] == 1


def test_multiple_affected_files():

    calls = [
        make_call(file_path="app.py"),
        make_call(file_path="payment.py"),
    ]

    report = detect_breaking_usage(
        [make_change()],
        calls,
    )

    assert report["affected_file_count"] == 2

    assert report["affected_call_site_count"] == 2

    assert report["affected_files"] == [
        "app.py",
        "payment.py",
    ]


def test_repository_usage_integration(tmp_path):

    (tmp_path / "app.py").write_text(
        "from paymentlib import pay as process\n"
        "process(500, currency='INR')\n",
        encoding="utf-8",
    )

    comparison = {
        "comparison_status": "completed",
        "package": "paymentlib",
        "baseline_version": "1.0.0",
        "candidate_version": "2.0.0",
        "changes": [
            make_change(
                "PARAMETER_REMOVED",
                parameter="currency",
            )
        ],
    }

    report = analyze_repository_usage(
        tmp_path,
        comparison,
    )

    assert report["total_findings"] == 1

    assert report["direct_usage_findings"] == 1

    assert report["findings"][0]["line"] == 2

    assert (
        report["findings"][0]["file_path"]
        == "app.py"
    )

    assert not report[
        "runtime_compatibility_verified"
    ]


def test_incomplete_comparison_rejected(tmp_path):

    comparison = {
        "comparison_status": "incomplete",
        "changes": [],
    }

    with pytest.raises(ValueError):

        analyze_repository_usage(
            tmp_path,
            comparison,
        )


def test_missing_changes_rejected(tmp_path):

    comparison = {
        "comparison_status": "completed",
    }

    with pytest.raises(ValueError):

        analyze_repository_usage(
            tmp_path,
            comparison,
        )


def test_limited_resolver_coverage(tmp_path):

    (tmp_path / "app.py").write_text(
        "import paymentlib\n"
        "if condition:\n"
        "    paymentlib.pay()\n",
        encoding="utf-8",
    )

    comparison = {
        "comparison_status": "completed",
        "changes": [make_change()],
    }

    report = analyze_repository_usage(
        tmp_path,
        comparison,
    )

    assert report["coverage_status"] == "limited"

    assert report["resolver_warning_count"] > 0

    assert report["total_findings"] == 0

    assert not report[
        "runtime_compatibility_verified"
    ]


def test_empty_breaking_changes():

    report = detect_breaking_usage(
        [],
        [make_call()],
    )

    assert report["total_breaking_changes"] == 0

    assert report["total_findings"] == 0

    assert report["affected_file_count"] == 0
