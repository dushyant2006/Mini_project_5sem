
import json

from unittest.mock import patch

from codedrift.repository.analyzer import (
    analyze_local_repository,
    analyze_github_repository,
)


def test_local_repository_analysis(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "requests==2.28.0\n",
        encoding="utf-8",
    )

    report = analyze_local_repository(
        tmp_path,
        offline=True,
    )

    assert report["dependency_count"] == 1

    dependency = report["dependencies"][0]

    assert dependency["name"] == "requests"
    assert dependency["baseline_version"] == "2.28.0"
    assert dependency["comparison_status"] == "not_checked"


def test_online_update_detection(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "requests==2.28.0\n",
        encoding="utf-8",
    )

    with patch(
        "codedrift.dependency.registry_client.get_latest_release",
        return_value="2.32.0",
    ):

        report = analyze_local_repository(tmp_path)

    assert report["updates_found"] == 1

    dependency = report["dependencies"][0]

    assert dependency["latest_release"] == "2.32.0"
    assert dependency["comparison_status"] == "update_available"


def test_unresolved_dependency(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "requests>=2.28.0\n",
        encoding="utf-8",
    )

    report = analyze_local_repository(
        tmp_path,
        offline=True,
    )

    assert report["unresolved_versions"] == 1


def test_npm_lockfile_integration(tmp_path):

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
                    "axios": "^1.6.0"
                }
            },
            "node_modules/axios": {
                "version": "1.7.2"
            }
        }
    }

    (tmp_path / "package.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    (tmp_path / "package-lock.json").write_text(
        json.dumps(lockfile),
        encoding="utf-8",
    )

    with patch(
        "codedrift.dependency.registry_client.get_latest_release",
        return_value="2.0.0",
    ):

        report = analyze_local_repository(tmp_path)

    dependency = report["dependencies"][0]

    assert dependency["constraint"] == "^1.6.0"
    assert dependency["baseline_version"] == "1.7.2"
    assert dependency["latest_release"] == "2.0.0"
    assert report["updates_found"] == 1


def test_github_repository_analysis():

    downloaded_paths = []

    def fake_clone(url, destination):

        destination.mkdir()

        (destination / "requirements.txt").write_text(
            "flask==2.2.0\n",
            encoding="utf-8",
        )

        downloaded_paths.append(destination)

        return destination

    with patch(
        "codedrift.repository.analyzer.clone_repository",
        side_effect=fake_clone,
    ):

        report = analyze_github_repository(
            "https://github.com/owner/demo",
            offline=True,
        )

    assert report["repository"] == "demo"
    assert report["dependency_count"] == 1
    assert report["dependencies"][0]["name"] == "flask"
    assert not downloaded_paths[0].exists()
