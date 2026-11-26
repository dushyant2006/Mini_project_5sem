
import pytest

from pathlib import Path
from unittest.mock import patch

from codedrift.dependency.package_comparator import (
    compare_source_directories,
    compare_package_versions,
    PackageComparisonError,
)


PREPARE = (
    "codedrift.dependency.package_comparator."
    "prepare_package"
)


def write_source(root, relative_path, content):

    path = root / relative_path

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        content,
        encoding="utf-8",
    )

    return path


def create_versions(tmp_path, old_code, new_code):

    old = tmp_path / "old"

    new = tmp_path / "new"

    write_source(
        old,
        "demo/api.py",
        old_code,
    )

    write_source(
        new,
        "demo/api.py",
        new_code,
    )

    return old, new


def test_removed_function(tmp_path):

    old, new = create_versions(
        tmp_path,
        "def calculate(): pass\n",
        "def replacement(): pass\n",
    )

    report = compare_source_directories(
        old,
        new,
    )

    assert report["comparison_status"] == "completed"

    assert report["breaking_count"] == 1

    assert any(
        change["qualified_name"] == "demo.api.calculate"
        and change["is_breaking"]
        for change in report["changes"]
    )


def test_removed_parameter(tmp_path):

    old, new = create_versions(
        tmp_path,
        "def calculate(a, b): pass\n",
        "def calculate(a): pass\n",
    )

    report = compare_source_directories(
        old,
        new,
    )

    assert report["breaking_count"] == 1

    assert any(
        change.get("parameter_name") == "b"
        and change["is_breaking"]
        for change in report["changes"]
    )


def test_added_optional_parameter(tmp_path):

    old, new = create_versions(
        tmp_path,
        "def calculate(a): pass\n",
        "def calculate(a, b=10): pass\n",
    )

    report = compare_source_directories(
        old,
        new,
    )

    assert report["breaking_count"] == 0

    assert report["non_breaking_count"] == 1


def test_unchanged_package(tmp_path):

    old, new = create_versions(
        tmp_path,
        "def calculate(a): pass\n",
        "def calculate(a): pass\n",
    )

    report = compare_source_directories(
        old,
        new,
    )

    assert report["comparison_status"] == "completed"

    assert report["total_changes"] == 0

    assert report["breaking_count"] == 0


def test_incomplete_parsing(tmp_path):

    old, new = create_versions(
        tmp_path,
        "def calculate(): pass\n",
        "def calculate(",
    )

    report = compare_source_directories(
        old,
        new,
    )

    assert report["comparison_status"] == "incomplete"

    assert report["breaking_count"] is None

    assert report["total_changes"] is None

    assert report["candidate_api"]["failed_files"] == 1

    assert report["changes"] == []


def test_private_function_ignored(tmp_path):

    old, new = create_versions(
        tmp_path,
        "def calculate(): pass\n"
        "def _helper(): pass\n",
        "def calculate(): pass\n",
    )

    report = compare_source_directories(
        old,
        new,
    )

    assert report["total_changes"] == 0


def test_include_private_functions(tmp_path):

    old, new = create_versions(
        tmp_path,
        "def calculate(): pass\n"
        "def _helper(): pass\n",
        "def calculate(): pass\n",
    )

    report = compare_source_directories(
        old,
        new,
        public_only=False,
    )

    assert report["breaking_count"] == 1


def test_severity_distribution(tmp_path):

    old, new = create_versions(
        tmp_path,
        "def calculate(): pass\n",
        "def replacement(): pass\n",
    )

    report = compare_source_directories(
        old,
        new,
    )

    assert sum(
        report["severity_distribution"].values()
    ) == report["total_changes"]

    assert sum(
        report["change_type_distribution"].values()
    ) == report["total_changes"]


def test_invalid_version_order():

    with pytest.raises(PackageComparisonError):

        compare_package_versions(
            "demo",
            "2.0.0",
            "1.0.0",
        )


def test_identical_versions():

    with pytest.raises(PackageComparisonError):

        compare_package_versions(
            "demo",
            "1.0.0",
            "1.0.0",
        )


def test_automatic_package_comparison():

    workspaces = []

    def fake_prepare(name, version, workspace):

        workspace = Path(workspace)

        workspaces.append(workspace)

        source = workspace / version / "sources"

        if version == "1.0.0":

            content = "def calculate(a, b): pass\n"

        else:

            content = "def calculate(a): pass\n"

        write_source(
            source,
            "demo/api.py",
            content,
        )

        return {
            "name": name,
            "version": version,
            "archive": str(
                workspace / f"demo-{version}.whl"
            ),
            "source_directory": str(source),
            "python_file_count": 1,
        }

    with patch(
        PREPARE,
        side_effect=fake_prepare,
    ) as mocked_prepare:

        report = compare_package_versions(
            "demo",
            "1.0.0",
            "2.0.0",
        )

    assert mocked_prepare.call_count == 2

    assert report["package"] == "demo"

    assert report["baseline_version"] == "1.0.0"

    assert report["candidate_version"] == "2.0.0"

    assert report["comparison_status"] == "completed"

    assert report["breaking_count"] == 1

    assert all(
        not workspace.exists()
        for workspace in workspaces
    )
