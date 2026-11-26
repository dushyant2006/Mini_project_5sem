
import argparse
import json
import tempfile

from collections import Counter
from pathlib import Path

from packaging.version import Version

from codedrift.dependency.package_downloader import (
    prepare_package,
    validate_package,
    PackageDownloadError,
)

from codedrift.parser.package_parser import PackageParser

from codedrift.detection.diff_engine import DiffEngine


class PackageComparisonError(Exception):
    pass


def summarize_package(result):

    summary = result.to_dict()

    summary.pop("modules")

    return summary


def compare_source_directories(
    old_directory,
    new_directory,
    public_only=True,
):

    parser = PackageParser()

    old_result = parser.parse_package(
        old_directory,
        public_only=public_only,
    )

    new_result = parser.parse_package(
        new_directory,
        public_only=public_only,
    )

    old_summary = summarize_package(old_result)

    new_summary = summarize_package(new_result)

    report = {
        "baseline_api": old_summary,
        "candidate_api": new_summary,
        "public_only": public_only,
        "comparison_status": "incomplete",
        "total_changes": None,
        "breaking_count": None,
        "non_breaking_count": None,
        "severity_distribution": {},
        "change_type_distribution": {},
        "changes": [],
    }

    if (
        not old_summary["complete"]
        or not new_summary["complete"]
    ):

        report["reason"] = (
            "One or both package versions "
            "could not be completely parsed."
        )

        return report

    engine = DiffEngine()

    diff = engine.compare_packages(
        old_result.modules,
        new_result.modules,
    )

    changes = [
        change.to_dict()
        for change in diff.changes
    ]

    changes.sort(
        key=lambda change: (
            change["qualified_name"],
            change["change_type"],
            change.get("parameter_name") or "",
        )
    )

    severity_distribution = Counter(
        change["severity"]
        for change in changes
    )

    change_type_distribution = Counter(
        change["change_type"]
        for change in changes
    )

    report.update({
        "comparison_status": "completed",
        "total_changes": len(changes),
        "breaking_count": len(
            diff.breaking_changes
        ),
        "non_breaking_count": len(
            diff.non_breaking_changes
        ),
        "severity_distribution": dict(
            sorted(severity_distribution.items())
        ),
        "change_type_distribution": dict(
            sorted(change_type_distribution.items())
        ),
        "changes": changes,
    })

    return report


def compare_package_versions(
    name,
    old_version,
    new_version,
    public_only=True,
):

    name, old_version = validate_package(
        name,
        old_version,
    )

    _, new_version = validate_package(
        name,
        new_version,
    )

    if Version(old_version) >= Version(new_version):

        raise PackageComparisonError(
            "Candidate version must be newer "
            "than baseline version."
        )

    with tempfile.TemporaryDirectory(
        prefix="codedrift_compare_"
    ) as workspace:

        workspace = Path(workspace)

        old_package = prepare_package(
            name,
            old_version,
            workspace,
        )

        new_package = prepare_package(
            name,
            new_version,
            workspace,
        )

        report = compare_source_directories(
            old_package["source_directory"],
            new_package["source_directory"],
            public_only=public_only,
        )

        return {
            "package": name,
            "ecosystem": "pypi",
            "baseline_version": old_version,
            "candidate_version": new_version,
            "baseline_artifact": Path(
                old_package["archive"]
            ).name,
            "candidate_artifact": Path(
                new_package["archive"]
            ).name,
            "analysis_method": "static_ast",
            **report,
        }


def main():

    parser = argparse.ArgumentParser(
        description=(
            "CodeDrift automatic Python "
            "package version comparator"
        )
    )

    parser.add_argument("name")

    parser.add_argument("old_version")

    parser.add_argument("new_version")

    parser.add_argument(
        "--include-private",
        action="store_true",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Exclude individual API changes",
    )

    args = parser.parse_args()

    try:

        report = compare_package_versions(
            args.name,
            args.old_version,
            args.new_version,
            public_only=not args.include_private,
        )

        if args.summary:

            report.pop("changes")

        print(json.dumps(report, indent=2))

        if report["comparison_status"] != "completed":

            return 1

        return 0

    except (
        PackageDownloadError,
        PackageComparisonError,
        OSError,
        ValueError,
    ) as error:

        parser.exit(
            status=1,
            message=f"CodeDrift error: {error}\n",
        )


if __name__ == "__main__":

    raise SystemExit(main())
