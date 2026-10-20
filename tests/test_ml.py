"""
Unit Tests for CodeDrift ML Feature Extraction and Degradation Prediction.
"""
from codedrift.ml import DegradationFeatureExtractor, DegradationPredictor
from codedrift.core.models import DiffResult, APIChange, BlastRadiusReport, BlastRadiusItem


def test_feature_extractor_computes_ratios():
    diff = DiffResult(
        changes=[
            APIChange("FN_REM", "lib.foo", is_breaking=True, severity="CRITICAL"),
            APIChange("FN_ADD", "lib.bar", is_breaking=False, severity="LOW"),
        ]
    )
    extractor = DegradationFeatureExtractor()
    features = extractor.extract(diff)

    assert features.total_changes == 2
    assert features.breaking_changes == 1
    assert features.breaking_ratio == 0.5
    assert features.critical_count == 1


def test_predictor_estimates_high_risk_on_reachable_breaks():
    diff = DiffResult(
        changes=[
            APIChange("FN_REM", "lib.foo", is_breaking=True, severity="CRITICAL"),
        ]
    )
    report = BlastRadiusReport(
        client_dir="client",
        total_breaking_upstream=1,
        reachable_breaking_count=1,
        blast_radius_score=85.0,
        items=[
            BlastRadiusItem(
                change=diff.changes[0],
                call_sites=[],
                is_reachable=True,
                impact_score=1.0,
            )
        ],
        affected_files=["app.py"],
    )

    predictor = DegradationPredictor()
    pred = predictor.predict(diff, blast_report=report)

    assert pred.degradation_probability > 0.5
    assert pred.risk_tier in ("MODERATE_RISK", "SEVERE_REGRESSION")
    assert pred.estimated_remediation_hours > 0.0
    assert len(pred.key_risk_drivers) > 0
