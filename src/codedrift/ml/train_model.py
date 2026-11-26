
import argparse
import json

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier

from sklearn.model_selection import GroupShuffleSplit

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)

from codedrift.ml.risk_features import FEATURE_NAMES


def train_risk_model(
    dataset,
    seed=42,
):

    required = set(
        FEATURE_NAMES + [
            "label",
            "group",
            "source",
        ]
    )

    missing = required - set(dataset.columns)

    if missing:

        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    if len(dataset) < 100:

        raise ValueError(
            "At least 100 labeled samples are required."
        )

    if dataset["group"].nunique() < 5:

        raise ValueError(
            "At least five repository groups are required."
        )

    if set(dataset["label"].unique()) != {0, 1}:

        raise ValueError(
            "Both binary labels are required."
        )

    sources = dataset["source"].unique()

    if len(sources) != 1 or sources[0] not in {
        "synthetic", "observed"
    }:

        raise ValueError(
            "Use either synthetic or observed data, not both."
        )

    source = str(sources[0])

    X = dataset[FEATURE_NAMES].astype(float)

    y = dataset["label"].astype(int)

    if not np.isfinite(X.to_numpy()).all():

        raise ValueError(
            "Features must contain finite numbers."
        )

    if (X < 0).any().any():

        raise ValueError(
            "Features cannot be negative."
        )

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.2,
        random_state=seed,
    )

    train_index, test_index = next(
        splitter.split(
            X,
            y,
            groups=dataset["group"],
        )
    )

    X_train = X.iloc[train_index]
    X_test = X.iloc[test_index]

    y_train = y.iloc[train_index]
    y_test = y.iloc[test_index]

    if (
        y_train.nunique() != 2
        or y_test.nunique() != 2
    ):

        raise ValueError(
            "Both training and test sets need both labels."
        )

    model = RandomForestClassifier(
        n_estimators=150,
        max_depth=12,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
    )

    model.fit(
        X_train,
        y_train,
    )

    predictions = model.predict(X_test)

    probabilities = model.predict_proba(
        X_test
    )[:, 1]

    metrics = {
        "accuracy": float(
            accuracy_score(y_test, predictions)
        ),
        "precision": float(
            precision_score(
                y_test,
                predictions,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                y_test,
                predictions,
                zero_division=0,
            )
        ),
        "f1_score": float(
            f1_score(
                y_test,
                predictions,
                zero_division=0,
            )
        ),
        "roc_auc": float(
            roc_auc_score(
                y_test,
                probabilities,
            )
        ),
        "confusion_matrix": confusion_matrix(
            y_test,
            predictions,
            labels=[0, 1],
        ).tolist(),
    }

    metadata = {
        "model_type": "RandomForestClassifier",
        "schema_version": 1,
        "dataset_source": source,
        "demo_only": source == "synthetic",
        "total_samples": len(dataset),
        "training_samples": len(train_index),
        "testing_samples": len(test_index),
        "split_method": "repository_group_holdout",
        "features": FEATURE_NAMES,
        "metrics": metrics,
        "feature_importance": {
            name: float(value)
            for name, value in zip(
                FEATURE_NAMES,
                model.feature_importances_,
            )
        },
        "probability_calibrated": False,
    }

    return {
        "model": model,
        "metadata": metadata,
    }


def save_model(bundle, output_path):

    path = Path(output_path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(bundle, path)

    metrics_path = path.with_suffix(".json")

    metrics_path.write_text(
        json.dumps(
            bundle["metadata"],
            indent=2,
        ),
        encoding="utf-8",
    )

    return path


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset",
        default="data/ml/upgrade_dataset.csv",
    )

    parser.add_argument(
        "--output",
        default="data/ml/risk_model.joblib",
    )

    args = parser.parse_args()

    dataset = pd.read_csv(args.dataset)

    bundle = train_risk_model(dataset)

    path = save_model(
        bundle,
        args.output,
    )

    print(f"Model saved: {path}")

    print(json.dumps(
        bundle["metadata"],
        indent=2,
    ))


if __name__ == "__main__":

    main()

