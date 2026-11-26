
import json

from codedrift.dependency.version_resolver import (
    resolve_dependency,
)


def test_exact_python_version(tmp_path):

    dependency = {
        "name": "requests",
        "ecosystem": "pypi",
        "constraint": "==2.28.0",
        "source": "requirements.txt",
        "group": "runtime",
    }

    result = resolve_dependency(
        dependency, tmp_path
    )

    assert result["baseline_version"] == "2.28.0"

    assert result["version_source"] == "declared_pin"


def test_python_version_range(tmp_path):

    dependency = {
        "name": "requests",
        "ecosystem": "pypi",
        "constraint": ">=2.28.0",
        "source": "requirements.txt",
        "group": "runtime",
    }

    result = resolve_dependency(
        dependency, tmp_path
    )

    assert result["baseline_version"] is None

    assert result["version_source"] == "unresolved"


def create_npm_project(
    path,
    locked_constraint="^1.6.0",
):

    manifest = {
        "dependencies": {
            "axios": "^1.6.0"
        }
    }

    lockfile = {
        "lockfileVersion": 3,
        "packages": {
            "": {
                "dependencies": {
                    "axios": locked_constraint
                }
            },
            "node_modules/axios": {
                "version": "1.7.2"
            }
        }
    }

    (path / "package.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    (path / "package-lock.json").write_text(
        json.dumps(lockfile),
        encoding="utf-8",
    )


def test_npm_lockfile_resolution(tmp_path):

    create_npm_project(tmp_path)

    dependency = {
        "name": "axios",
        "ecosystem": "npm",
        "constraint": "^1.6.0",
        "source": "package.json",
        "group": "runtime",
    }

    result = resolve_dependency(
        dependency, tmp_path
    )

    assert result["baseline_version"] == "1.7.2"

    assert result["version_source"] == "package-lock.json"


def test_stale_npm_lockfile(tmp_path):

    create_npm_project(
        tmp_path,
        locked_constraint="^0.9.0",
    )

    dependency = {
        "name": "axios",
        "ecosystem": "npm",
        "constraint": "^1.6.0",
        "source": "package.json",
        "group": "runtime",
    }

    result = resolve_dependency(
        dependency, tmp_path
    )

    assert result["baseline_version"] is None

    assert result["version_source"] == "unresolved"


def test_missing_npm_lockfile(tmp_path):

    dependency = {
        "name": "react",
        "ecosystem": "npm",
        "constraint": "^18.2.0",
        "source": "package.json",
        "group": "runtime",
    }

    result = resolve_dependency(
        dependency, tmp_path
    )

    assert result["baseline_version"] is None

    assert result["version_source"] == "unresolved"


def test_exact_maven_version(tmp_path):

    dependency = {
        "name": "org.junit.jupiter:junit-jupiter",
        "ecosystem": "maven",
        "constraint": "5.10.0",
        "source": "pom.xml",
        "group": "runtime",
    }

    result = resolve_dependency(
        dependency, tmp_path
    )

    assert result["baseline_version"] == "5.10.0"

    assert result["version_source"] == "declared_pin"
