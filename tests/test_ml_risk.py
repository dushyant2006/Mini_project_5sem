
import json

import pytest

from codedrift.ml.risk_features import (
    FEATURE_NAMES,
    version_features,
    extract_risk_features,
    feature_vector,
)

from codedrift.ml.dataset_builder import (
    generate_demo_dataset,
    build_real_dataset,
)

from codedrift.ml.train_model import (
    train_risk_model,
    save_model,
)

from codedrift.ml.risk_predictor import (
    RiskPredictor,
    classify_ml_risk,
    enrich_report,
)


def make_dependency(**overrides):

    dependency = {
        "name": "paymentlib",
        "ecosystem": "pypi",
        "baseline_version": "1.0.0",
        "latest_release": "2.0.0",
        "comparison_status": "update_available",
        "api_analysis_status": "completed",
        "impact_analysis_status": "completed",
        "api_breaking_count": 2,
        "api_comparison": {
            "changes": [
                {
                    "is_breaking": True,
                    "severity": "CRITICAL",
                },
                {
                    "is_breaking": True,
                    "severity": "HIGH",
                },
            ]
        },
        "impact_report": {
            "direct_usage_findings": 2,
            "potential_impact_findings": 1,
            "affected_file_count": 2,
            "coverage_limited": False,
        },
    }

    dependency.update(overrides)

    return dependency


@pytest.fixture(scope="module")
def trained_bundle():

    dataset = generate_demo_dataset(
        sample_count=500
    )

    return train_risk_model(dataset)


@pytest.fixture
def model_path(
    tmp_path,
    trained_bundle,
):

    return save_model(
        trained_bundle,
        tmp_path / "model.joblib",
    )


def test_major_version():

    assert version_features(
        "1.0.0", "2.0.0"
    ) == (1, 0, 0)


def test_minor_version():

    assert version_features(
        "1.0.0", "1.2.0"
    ) == (0, 1, 0)


def test_patch_version():

    assert version_features(
        "1.0.0", "1.0.1"
    ) == (0, 0, 1)


def test_invalid_version():

    assert version_features(
        "invalid", "2.0.0"
    ) == (0, 0, 0)


def test_downgrade():

    assert version_features(
        "2.0.0", "1.0.0"
    ) == (0, 0, 0)


def test_feature_extraction():

    features = extract_risk_features(
        make_dependency()
    )

    assert features["major_upgrade"] == 1

    assert features["breaking_count"] == 2

    assert features["critical_count"] == 1

    assert features["direct_usage_count"] == 2


def test_feature_vector():

    features = extract_risk_features(
        make_dependency()
    )

    assert len(
        feature_vector(features)
    ) == len(FEATURE_NAMES)


def test_unsupported_ecosystem():

    dependency = make_dependency(
        ecosystem="npm"
    )

    assert extract_risk_features(
        dependency
    ) is None


def test_incomplete_api_analysis():

    dependency = make_dependency(
        api_analysis_status="failed"
    )

    assert extract_risk_features(
        dependency
    ) is None


def test_incomplete_impact_analysis():

    dependency = make_dependency(
        impact_analysis_status="comparison_unavailable"
    )

    assert extract_risk_features(
        dependency
    ) is None


def test_unresolved_version():

    dependency = make_dependency(
        baseline_version=None
    )

    assert extract_risk_features(
        dependency
    ) is None


def test_demo_dataset():

    dataset = generate_demo_dataset(500)

    assert len(dataset) == 500

    assert set(dataset["label"]) == {0, 1}

    assert set(dataset["source"]) == {"synthetic"}


def test_dataset_reproducibility():

    first = generate_demo_dataset(100)

    second = generate_demo_dataset(100)

    assert first.equals(second)


def test_real_dataset(tmp_path):

    path = tmp_path / "outcomes.json"

    path.write_text(
        json.dumps([
            {
                "repository": "owner/demo",
                "baseline_tests_passed": True,
                "candidate_tests_passed": False,
                "controlled_upgrade": True,
                "dependency": make_dependency(),
            }
        ]),
        encoding="utf-8",
    )

    dataset = build_real_dataset(path)

    assert len(dataset) == 1

    assert dataset.iloc[0]["label"] == 1

    assert dataset.iloc[0]["source"] == "observed"


def test_failed_baseline_excluded(tmp_path):

    path = tmp_path / "outcomes.json"

    path.write_text(
        json.dumps([
            {
                "repository": "owner/demo",
                "baseline_tests_passed": False,
                "candidate_tests_passed": False,
                "controlled_upgrade": True,
                "dependency": make_dependency(),
            }
        ]),
        encoding="utf-8",
    )

    assert build_real_dataset(path).empty


def test_model_training(trained_bundle):

    assert trained_bundle["model"] is not None

    assert trained_bundle["metadata"]["demo_only"]


def test_model_metrics(trained_bundle):

    metrics = trained_bundle["metadata"]["metrics"]

    for name in [
        "accuracy",
        "precision",
        "recall",
        "f1_score",
        "roc_auc",
    ]:

        assert 0 <= metrics[name] <= 1


def test_model_persistence(model_path):

    assert model_path.exists()

    assert model_path.with_suffix(".json").exists()


def test_missing_model(tmp_path):

    predictor = RiskPredictor(
        tmp_path / "missing.joblib"
    )

    result = predictor.predict(
        make_dependency()
    )

    assert result["status"] == "unavailable"


def test_demo_disabled_by_default(model_path):

    predictor = RiskPredictor(model_path)

    result = predictor.predict(
        make_dependency()
    )

    assert result["status"] == "unavailable"


def test_demo_prediction(model_path):

    predictor = RiskPredictor(
        model_path,
        allow_demo=True,
    )

    result = predictor.predict(
        make_dependency()
    )

    assert result["status"] == "demo_prediction"

    assert 0 <= result["risk_score"] <= 100

    assert result["demo_only"]

    assert not result["safe_to_auto_merge"]


def test_risk_classification():

    assert classify_ml_risk(0.1) == "LOW"

    assert classify_ml_risk(0.5) == "MEDIUM"

    assert classify_ml_risk(0.9) == "HIGH"


def test_report_integration(model_path):

    report = {
        "repository": "demo",
        "dependencies": [
            make_dependency(),
            make_dependency(
                api_analysis_status="failed"
            ),
        ],
    }

    result = enrich_report(
        report,
        model_path=model_path,
        allow_demo=True,
    )

    assert result["ml_analysis"][
        "predictions_completed"
    ] == 1

    assert result["ml_analysis"][
        "predictions_unavailable"
    ] == 1


def test_original_report_preserved(model_path):

    report = {
        "dependencies": [
            make_dependency()
        ]
    }

    enrich_report(
        report,
        model_path=model_path,
        allow_demo=True,
    )

    assert "ml_prediction" not in (
        report["dependencies"][0]
    )


def test_empty_report(model_path):

    result = enrich_report(
        {"dependencies": []},
        model_path=model_path,
        allow_demo=True,
    )

    assert result["ml_analysis"][
        "predictions_completed"
    ] == 0
