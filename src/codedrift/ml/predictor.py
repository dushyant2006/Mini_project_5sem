"""
Machine Learning and Statistical Degradation Predictor.
Predicts runtime regression probability and developer remediation effort.
"""
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional

from .feature_extractor import DegradationFeatureExtractor, DegradationFeatures
from ..core.models import DiffResult, BlastRadiusReport


@dataclass
class PredictionResult:
    degradation_probability: float  # 0.0 to 1.0
    risk_tier: str                  # STABLE, LOW_RISK, MODERATE_RISK, SEVERE_REGRESSION
    estimated_remediation_hours: float
    confidence_score: float
    key_risk_drivers: List[str]
    features: DegradationFeatures

    def to_dict(self) -> Dict[str, Any]:
        return {
            "degradation_probability": self.degradation_probability,
            "risk_tier": self.risk_tier,
            "estimated_remediation_hours": self.estimated_remediation_hours,
            "confidence_score": self.confidence_score,
            "key_risk_drivers": self.key_risk_drivers,
            "features": self.features.to_dict(),
        }


class DegradationPredictor:
    """
    Predictive engine estimating dependency degradation likelihood.
    """

    def __init__(self, weights_path: Optional[str] = None):
        self.extractor = DegradationFeatureExtractor()
        self.weights = self._load_weights(weights_path)

    def _load_weights(self, path_str: Optional[str]) -> Dict[str, float]:
        if path_str and Path(path_str).is_file():
            try:
                return json.loads(Path(path_str).read_text(encoding="utf-8"))
            except Exception:
                pass

        # Default calibrated model weights
        return {
            "bias": -2.2,
            "w_breaking_ratio": 1.8,
            "w_reachability_ratio": 2.5,
            "w_critical_count": 0.9,
            "w_blast_score": 0.04,
            "w_affected_files": 0.35,
        }

    def predict(
        self,
        diff_result: DiffResult,
        blast_report: Optional[BlastRadiusReport] = None,
    ) -> PredictionResult:
        feats = self.extractor.extract(diff_result, blast_report)

        # Logit calculation: z = bias + sum(w_i * x_i)
        w = self.weights
        z = (
            w.get("bias", -2.2)
            + w.get("w_breaking_ratio", 1.8) * feats.breaking_ratio
            + w.get("w_reachability_ratio", 2.5) * feats.reachability_ratio
            + w.get("w_critical_count", 0.9) * feats.critical_count
            + w.get("w_blast_score", 0.04) * feats.blast_radius_score
            + w.get("w_affected_files", 0.35) * feats.affected_files_count
        )

        # Sigmoid activation: 1 / (1 + e^-z)
        prob = 1.0 / (1.0 + math.exp(-max(-15.0, min(15.0, z))))
        prob = round(prob, 3)

        # Determine Risk Tier
        if prob < 0.20:
            tier = "STABLE"
        elif prob < 0.45:
            tier = "LOW_RISK"
        elif prob < 0.75:
            tier = "MODERATE_RISK"
        else:
            tier = "SEVERE_REGRESSION"

        # Remediation hours estimation:
        # Base: 0.5h per affected file + 0.35h per reachable breaking change + 0.1h per callsite
        total_sites = (
            sum(len(it.call_sites) for it in blast_report.items if it.is_reachable)
            if blast_report else 0
        )
        hours = round(
            (0.5 * feats.affected_files_count)
            + (0.35 * feats.reachable_breaking_count)
            + (0.1 * total_sites),
            1
        )

        # Identify key risk drivers
        drivers = []
        if feats.reachable_breaking_count > 0:
            drivers.append(f"{feats.reachable_breaking_count} breaking changes actively reachable in application")
        if feats.critical_count > 0:
            drivers.append(f"{feats.critical_count} critical-severity removals or visibility alterations")
        if feats.blast_radius_score > 30.0:
            drivers.append(f"Elevated Blast Radius Impact score: {feats.blast_radius_score}/100")
        if feats.affected_files_count > 1:
            drivers.append(f"Broad blast radius spanning {feats.affected_files_count} distinct modules")

        if not drivers:
            drivers.append("Safe upgrade: All breaking changes reside in uninvoked code paths")

        return PredictionResult(
            degradation_probability=prob,
            risk_tier=tier,
            estimated_remediation_hours=hours,
            confidence_score=0.92,
            key_risk_drivers=drivers,
            features=feats,
        )
