
import pytest

from codedrift.dependency.manifest_scanner import (
    identify_manifest,
    scan_manifests,
    analyze_repository_structure,
)


def test_identify_python_manifest(tmp_path):
    file = tmp_path / "requirements.txt"
    file.write_text("requests==2.28.0")

    assert identify_manifest(file) == ("python", "pypi")


def test_identify_npm_manifest(tmp_path):
    file = tmp_path / "package.json"
    file.write_text('{"dependencies": {"react": "18.2.0"}}')

    assert identify_manifest(file) == ("javascript", "npm")


def test_identify_maven_manifest(tmp_path):
    file = tmp_path / "pom.xml"
    file.write_text("<project></project>")

    assert identify_manifest(file) == ("java", "maven")


def test_detect_multiple_ecosystems(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "flask==2.2.0"
    )
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "pom.xml").write_text("<project />")

    report = analyze_repository_structure(tmp_path)

    assert report["supported_manifests"] == 3
    assert report["ecosystems"] == [
        "maven", "npm", "pypi"
    ]


def test_skip_node_modules(tmp_path):
    ignored = tmp_path / "node_modules"
    ignored.mkdir()
    (ignored / "package.json").write_text("{}")

    result = scan_manifests(tmp_path)

    assert result == []


def test_scan_nested_manifest(tmp_path):
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "requirements-dev.txt").write_text(
        "pytest==8.3.4"
    )

    report = scan_manifests(tmp_path)

    assert report[0]["path"] == (
        "backend/requirements-dev.txt"
    )


def test_invalid_repository_path(tmp_path):
    missing = tmp_path / "not-found"

    with pytest.raises(ValueError):
        scan_manifests(missing)
