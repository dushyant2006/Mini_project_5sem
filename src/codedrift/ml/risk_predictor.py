
import argparse
import json

from pathlib import Path

import joblib
import pandas as pd

from codedrift.ml.risk_features import (
    FEATURE_NAMES,
    extract_risk_features,
)


DEFAULT_MODEL = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "ml"
    / "risk_model.joblib"
)


def classify_ml_risk(score):

    if score >= 0.70:
        return "HIGH"

    if score >= 0.35:
        return "MEDIUM"

    return "LOW"


class RiskPredictor:

    def __init__(
        self,
        model_path=DEFAULT_MODEL,
        allow_demo=False,
    ):

        self.model_path = Path(model_path)

        self.bundle = None

        self.allow_demo = allow_demo

        if self.model_path.is_file():

            self.bundle = joblib.load(
                self.model_path
            )

            metadata = self.bundle["metadata"]

            if (
                metadata.get("schema_version") != 1
                or metadata.get("features") != FEATURE_NAMES
            ):

                raise ValueError(
                    "Incompatible model feature schema."
                )

    def unavailable(self, reason):

        return {
            "status": "unavailable",
            "reason": reason,
            "risk_score": None,
            "risk_level": "UNKNOWN",
            "safe_to_auto_merge": False,
        }

    def predict(self, dependency):

        if self.bundle is None:

            return self.unavailable(
                "No trained model is available."
            )

        metadata = self.bundle["metadata"]

        if (
            metadata.get("demo_only")
            and not self.allow_demo
        ):

            return self.unavailable(
                "Synthetic model disabled for real predictions."
            )

        features = extract_risk_features(
            dependency
        )

        if features is None:

            return self.unavailable(
                "Insufficient completed analysis."
            )

        X = pd.DataFrame(
            [features],
            columns=FEATURE_NAMES,
        )

        model = self.bundle["model"]

        score = float(
            model.predict_proba(X)[0][1]
        )

        return {
            "status": (
                "demo_prediction"
                if metadata["demo_only"]
                else "prediction"
            ),
            "model_type": metadata["model_type"],
            "dataset_source": metadata["dataset_source"],
            "demo_only": metadata["demo_only"],
            "risk_score": round(score * 100, 2),
            "risk_level": classify_ml_risk(score),
            "features": features,
            "coverage_limited": bool(
                features["coverage_limited"]
            ),
            "probability_calibrated": False,
            "runtime_compatibility_verified": False,
            "safe_to_auto_merge": False,
        }


def enrich_report(
    report,
    model_path=DEFAULT_MODEL,
    allow_demo=False,
):

    predictor = RiskPredictor(
        model_path,
        allow_demo=allow_demo,
    )

    dependencies = []

    for dependency in report.get(
        "dependencies", []
    ):

        item = dict(dependency)

        item["ml_prediction"] = predictor.predict(
            dependency
        )

        dependencies.append(item)

    predicted = [
        item["ml_prediction"]
        for item in dependencies
        if item["ml_prediction"]["status"] in {
            "prediction",
            "demo_prediction",
        }
    ]

    distribution = {
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "UNKNOWN": len(dependencies) - len(predicted),
    }

    for prediction in predicted:

        distribution[
            prediction["risk_level"]
        ] += 1

    return {
        **report,
        "dependencies": dependencies,
        "ml_analysis": {
            "model_available": predictor.bundle is not None,
            "predictions_completed": len(predicted),
            "predictions_unavailable": (
                len(dependencies) - len(predicted)
            ),
            "demo_predictions": sum(
                item["status"] == "demo_prediction"
                for item in predicted
            ),
            "risk_distribution": distribution,
            "safe_to_auto_merge": False,
        },
    }


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "report",
        help="Existing CodeDrift JSON analysis report",
    )

    parser.add_argument(
        "--model",
        default=str(DEFAULT_MODEL),
    )

    parser.add_argument(
        "--allow-demo",
        action="store_true",
    )

    parser.add_argument(
        "--output",
        default="data/ml/prediction_report.json",
    )

    args = parser.parse_args()

    report = json.loads(
        Path(args.report).read_text(
            encoding="utf-8-sig"
        )
    )

    if "analysis_report" in report:

        report = report["analysis_report"]

    enriched = enrich_report(
        report,
        model_path=args.model,
        allow_demo=args.allow_demo,
    )

    output = Path(args.output)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            enriched,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(json.dumps(
        enriched["ml_analysis"],
        indent=2,
    ))

    print(f"Prediction report saved: {output}")


if __name__ == "__main__":

    main()
