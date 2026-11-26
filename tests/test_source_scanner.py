
import ast

import pytest

from codedrift.impact.source_scanner import (
    SourceScanner,
)


def test_python_source_discovery(tmp_path):

    (tmp_path / "app.py").write_text(
        "print('Hello')\n",
        encoding="utf-8",
    )

    (tmp_path / "README.md").write_text(
        "# Demo",
        encoding="utf-8",
    )

    result = SourceScanner().scan_repository(
        tmp_path
    )

    assert result.discovered_files == 1

    assert len(result.files) == 1

    assert result.files[0].file_path == "app.py"

    assert result.complete is True


def test_nested_python_files(tmp_path):

    directory = tmp_path / "services"

    directory.mkdir()

    (directory / "payment.py").write_text(
        "def pay():\n    pass\n",
        encoding="utf-8",
    )

    result = SourceScanner().scan_repository(
        tmp_path
    )

    assert len(result.files) == 1

    assert (
        result.files[0].file_path
        == "services/payment.py"
    )


def test_ast_generation(tmp_path):

    (tmp_path / "app.py").write_text(
        "import requests\nrequests.get('https://example.com')\n",
        encoding="utf-8",
    )

    result = SourceScanner().scan_repository(
        tmp_path
    )

    assert isinstance(
        result.files[0].tree,
        ast.Module,
    )

    assert isinstance(
        result.files[0].tree.body[0],
        ast.Import,
    )


def test_ignored_directories(tmp_path):

    for name in [
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "build",
    ]:

        directory = tmp_path / name

        directory.mkdir()

        (directory / "ignored.py").write_text(
            "x = 1\n",
            encoding="utf-8",
        )

    (tmp_path / "app.py").write_text(
        "x = 2\n",
        encoding="utf-8",
    )

    result = SourceScanner().scan_repository(
        tmp_path
    )

    assert len(result.files) == 1

    assert len(result.ignored_directories) == 5


def test_syntax_error_reporting(tmp_path):

    (tmp_path / "broken.py").write_text(
        "def broken(\n",
        encoding="utf-8",
    )

    result = SourceScanner().scan_repository(
        tmp_path
    )

    assert len(result.errors) == 1

    assert result.errors[0]["file"] == "broken.py"

    assert (
        result.errors[0]["error_type"]
        == "SyntaxError"
    )

    assert result.complete is False


def test_scan_continues_after_error(tmp_path):

    (tmp_path / "broken.py").write_text(
        "def broken(\n",
        encoding="utf-8",
    )

    (tmp_path / "valid.py").write_text(
        "x = 1\n",
        encoding="utf-8",
    )

    result = SourceScanner().scan_repository(
        tmp_path
    )

    assert len(result.errors) == 1

    assert len(result.files) == 1

    assert result.discovered_files == 2


def test_large_file_skipped(tmp_path):

    (tmp_path / "large.py").write_text(
        "x = '1234567890'\n",
        encoding="utf-8",
    )

    scanner = SourceScanner(
        max_source_bytes=5
    )

    result = scanner.scan_repository(
        tmp_path
    )

    assert len(result.files) == 0

    assert len(result.skipped_files) == 1

    assert (
        result.skipped_files[0]["reason"]
        == "file_too_large"
    )

    assert result.complete is False


def test_source_file_limit(tmp_path):

    for name in ["a.py", "b.py", "c.py"]:

        (tmp_path / name).write_text(
            "x = 1\n",
            encoding="utf-8",
        )

    scanner = SourceScanner(
        max_files=2
    )

    result = scanner.scan_repository(
        tmp_path
    )

    assert len(result.files) == 2

    assert result.limit_reached is True

    assert result.complete is False


def test_source_encoding(tmp_path):

    (tmp_path / "app.py").write_bytes(
        "# coding: latin-1\nname = 'café'\n".encode(
            "latin-1"
        )
    )

    result = SourceScanner().scan_repository(
        tmp_path
    )

    assert len(result.files) == 1

    assert "café" in result.files[0].source_code


def test_empty_repository(tmp_path):

    result = SourceScanner().scan_repository(
        tmp_path
    )

    assert result.discovered_files == 0

    assert len(result.files) == 0

    assert result.complete is True


def test_missing_repository(tmp_path):

    with pytest.raises(NotADirectoryError):

        SourceScanner().scan_repository(
            tmp_path / "missing"
        )


def test_invalid_file_limit():

    with pytest.raises(ValueError):

        SourceScanner(max_files=0)


def test_invalid_source_size():

    with pytest.raises(ValueError):

        SourceScanner(max_source_bytes=0)


def test_source_scan_summary(tmp_path):

    (tmp_path / "app.py").write_text(
        "x = 1\ny = 2\n",
        encoding="utf-8",
    )

    result = SourceScanner().scan_repository(
        tmp_path
    )

    report = result.to_dict()

    assert report["parsed_files"] == 1

    assert report["total_lines"] == 2

    assert report["failed_files"] == 0

    assert report["skipped_file_count"] == 0

    assert report["complete"] is True

    assert report["files"][0]["file_path"] == "app.py"

    assert "tree" not in report["files"][0]

    assert "source_code" not in report["files"][0]


def test_source_code_not_executed(tmp_path):

    (tmp_path / "app.py").write_text(
        "raise RuntimeError('Do not execute')\n",
        encoding="utf-8",
    )

    result = SourceScanner().scan_repository(
        tmp_path
    )

    assert len(result.files) == 1

    assert len(result.errors) == 0

    assert result.complete is True

