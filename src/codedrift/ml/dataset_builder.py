
import argparse
import json
import random

from pathlib import Path

import pandas as pd

from codedrift.ml.risk_features import (
    FEATURE_NAMES,
    extract_risk_features,
)


def generate_demo_dataset(
    sample_count=3000,
    seed=42,
):

    if sample_count < 100:
        raise ValueError(
            "Generate at least 100 samples."
        )

    rng = random.Random(seed)

    rows = []

    for index in range(sample_count):

        upgrade = rng.choices(
            ["major", "minor", "patch"],
            weights=[25, 40, 35],
        )[0]

        maximum_breaks = {
            "major": 100,
            "minor": 25,
            "patch": 5,
        }[upgrade]

        breaking = rng.randint(
            0, maximum_breaks
        )

        critical = rng.randint(
            0, breaking
        )

        high = rng.randint(
            0, breaking - critical
        )

        direct = rng.randint(
            0, min(breaking, 12)
        )

        potential = rng.randint(
            0, min(breaking, 20)
        )

        affected = rng.randint(
            0, direct + potential
        )

        limited = rng.randint(0, 1)

        simulated_score = (
            0.8 * int(upgrade == "major")
            + 0.025 * breaking
            + 0.04 * critical
            + 0.35 * direct
            + 0.08 * potential
            + rng.gauss(0, 1.2)
            - 2.5
        )

        rows.append({
            "major_upgrade": int(upgrade == "major"),
            "minor_upgrade": int(upgrade == "minor"),
            "patch_upgrade": int(upgrade == "patch"),
            "breaking_count": breaking,
            "critical_count": critical,
            "high_count": high,
            "direct_usage_count": direct,
            "potential_usage_count": potential,
            "affected_files": affected,
            "coverage_limited": limited,
            "label": int(simulated_score > 0),
            "group": f"synthetic-project-{index % 100}",
            "source": "synthetic",
        })

    return pd.DataFrame(rows)


def build_real_dataset(outcomes_file):

    outcomes = json.loads(
        Path(outcomes_file).read_text(
            encoding="utf-8-sig"
        )
    )

    if not isinstance(outcomes, list):
        raise ValueError(
            "Outcomes must be a JSON array."
        )

    rows = []

    for outcome in outcomes:

        baseline_passed = outcome.get(
            "baseline_tests_passed"
        )

        candidate_passed = outcome.get(
            "candidate_tests_passed"
        )

        if baseline_passed is not True:
            continue

        if not isinstance(candidate_passed, bool):
            continue

        if outcome.get("controlled_upgrade") is not True:
            continue

        features = extract_risk_features(
            outcome["dependency"]
        )

        if features is None:
            continue

        group = outcome.get("repository")

        if not isinstance(group, str) or not group.strip():
            raise ValueError(
                "Repository identifier is required."
            )

        rows.append({
            **features,
            "label": int(not candidate_passed),
            "group": group,
            "source": "observed",
        })

    return pd.DataFrame(
        rows,
        columns=FEATURE_NAMES + [
            "label", "group", "source"
        ],
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--samples",
        type=int,
        default=3000,
    )

    parser.add_argument(
        "--outcomes",
        default=None,
    )

    parser.add_argument(
        "--output",
        default="data/ml/upgrade_dataset.csv",
    )

    args = parser.parse_args()

    if args.outcomes:

        dataset = build_real_dataset(
            args.outcomes
        )

    else:

        dataset = generate_demo_dataset(
            args.samples
        )

    if dataset.empty:
        raise ValueError(
            "No eligible training samples."
        )

    path = Path(args.output)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataset.to_csv(
        path,
        index=False,
    )

    print(f"Dataset saved: {path}")
    print(f"Total samples: {len(dataset)}")
    print(f"Source: {dataset['source'].unique()}")
    print("\nLabel distribution:")
    print(dataset["label"].value_counts())


if __name__ == "__main__":

    main()
