
import json

from unittest.mock import patch

from codedrift.repository.analyzer import (
    analyze_local_repository,
    analyze_github_repository,
)

from codedrift.security.osv_client import OSVError


REGISTRY = (
    "codedrift.dependency.registry_client.get_latest_release"
)

OSV = (
    "codedrift.security.osv_client.fetch_vulnerabilities"
)

COMPARATOR = (
    "codedrift.dependency.upgrade_analyzer."
    "compare_package_versions"
)


SAMPLE_ADVISORY = {
    "id": "TEST-001",
    "summary": "Synthetic test vulnerability",
    "aliases": ["CVE-2099-0001"],
    "affected": [
        {
            "package": {
                "name": "requests",
                "ecosystem": "PyPI",
            },
            "ranges": [
                {
                    "type": "ECOSYSTEM",
                    "events": [
                        {"introduced": "0"},
                        {"fixed": "2.32.0"},
                    ],
                }
            ],
        }
    ],
}


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
    assert dependency["security_status"] == "not_checked"


def test_online_update_detection(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "requests==2.28.0\n",
        encoding="utf-8",
    )

    with patch(REGISTRY, return_value="2.32.0"), \
         patch(OSV, return_value=[]):

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

    with patch(REGISTRY, return_value="2.0.0"), \
         patch(OSV, return_value=[]):

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


def test_repository_vulnerability_detection(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "requests==2.28.0\n",
        encoding="utf-8",
    )

    with patch(REGISTRY, return_value="2.32.0"), \
         patch(OSV, return_value=[SAMPLE_ADVISORY]):

        report = analyze_local_repository(tmp_path)

    assert report["vulnerable_dependencies"] == 1
    assert report["vulnerabilities_found"] == 1
    assert report["unique_cve_count"] == 1
    assert report["security_checked"] == 1

    dependency = report["dependencies"][0]

    assert dependency["security_status"] == "vulnerable"
    assert dependency["vulnerability_count"] == 1


def test_repository_no_known_vulnerabilities(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "requests==2.28.0\n",
        encoding="utf-8",
    )

    with patch(REGISTRY, return_value="2.32.0"), \
         patch(OSV, return_value=[]):

        report = analyze_local_repository(tmp_path)

    assert report["vulnerable_dependencies"] == 0
    assert report["vulnerabilities_found"] == 0
    assert report["security_checked"] == 1

    assert (
        report["dependencies"][0]["security_status"]
        == "no_known_vulnerabilities"
    )


def test_repository_security_failure(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "requests==2.28.0\n",
        encoding="utf-8",
    )

    with patch(REGISTRY, return_value="2.32.0"), \
         patch(OSV, side_effect=OSVError("Network failure")):

        report = analyze_local_repository(tmp_path)

    assert report["security_lookup_failures"] == 1
    assert report["security_checked"] == 0
    assert report["updates_found"] == 1

    dependency = report["dependencies"][0]

    assert dependency["security_status"] == "lookup_failed"
    assert dependency["vulnerability_count"] is None


def test_repository_unresolved_security(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "requests>=2.28.0\n",
        encoding="utf-8",
    )

    with patch(REGISTRY, return_value="2.32.0"), \
         patch(OSV) as osv_mock:

        report = analyze_local_repository(tmp_path)

    osv_mock.assert_not_called()

    assert report["security_unchecked"] == 1

    assert (
        report["dependencies"][0]["security_status"]
        == "unresolved_version"
    )


def test_offline_skips_external_requests(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "requests==2.28.0\n",
        encoding="utf-8",
    )

    with patch(REGISTRY) as registry_mock, \
         patch(OSV) as osv_mock:

        report = analyze_local_repository(
            tmp_path,
            offline=True,
        )

    registry_mock.assert_not_called()
    osv_mock.assert_not_called()

    assert report["security_unchecked"] == 1
    assert report["security_checked"] == 0


def test_security_cache(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "requests==2.28.0\n",
        encoding="utf-8",
    )

    subdirectory = tmp_path / "example"
    subdirectory.mkdir()

    (subdirectory / "requirements.txt").write_text(
        "requests==2.28.0\n",
        encoding="utf-8",
    )

    with patch(REGISTRY, return_value="2.32.0"), \
         patch(
             OSV,
             return_value=[SAMPLE_ADVISORY],
         ) as osv_mock:

        report = analyze_local_repository(tmp_path)

    osv_mock.assert_called_once()

    assert report["dependency_count"] == 2
    assert report["vulnerable_dependencies"] == 2
    assert report["unique_cve_count"] == 1
    assert report["unique_advisory_count"] == 1


def test_duplicate_cve_aliases(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "requests==2.28.0\n",
        encoding="utf-8",
    )

    duplicate = {
        **SAMPLE_ADVISORY,
        "id": "TEST-002",
    }

    with patch(REGISTRY, return_value="2.32.0"), \
         patch(
             OSV,
             return_value=[SAMPLE_ADVISORY, duplicate],
         ):

        report = analyze_local_repository(tmp_path)

    assert report["vulnerabilities_found"] == 2
    assert report["unique_advisory_count"] == 2
    assert report["unique_cve_count"] == 1


def test_repository_api_analysis(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "requests==2.28.0\n",
        encoding="utf-8",
    )

    comparison = {
        "comparison_status": "completed",
        "breaking_count": 2,
        "total_changes": 3,
        "non_breaking_count": 1,
        "changes": [],
    }

    with patch(REGISTRY, return_value="2.32.0"), \
         patch(OSV, return_value=[SAMPLE_ADVISORY]), \
         patch(
             COMPARATOR,
             return_value=comparison,
         ) as comparator:

        report = analyze_local_repository(
            tmp_path,
            breaking_changes=True,
        )

    comparator.assert_called_once_with(
        "requests",
        "2.28.0",
        "2.32.0",
    )

    assert report["updates_found"] == 1

    assert report["vulnerable_dependencies"] == 1

    assert (
        report["api_analysis"]["unique_breaking_findings"]
        == 2
    )

    assert (
        report["dependencies"][0]["api_analysis_status"]
        == "completed"
    )


def test_repository_api_analysis_disabled(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "requests==2.28.0\n",
        encoding="utf-8",
    )

    with patch(REGISTRY, return_value="2.32.0"), \
         patch(OSV, return_value=[]), \
         patch(COMPARATOR) as comparator:

        report = analyze_local_repository(tmp_path)

    comparator.assert_not_called()

    assert report["api_analysis"]["enabled"] is False

    assert (
        report["dependencies"][0]["api_analysis_status"]
        == "disabled"
    )


def test_repository_api_analysis_offline(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "requests==2.28.0\n",
        encoding="utf-8",
    )

    with patch(REGISTRY) as registry, \
         patch(OSV) as osv, \
         patch(COMPARATOR) as comparator:

        report = analyze_local_repository(
            tmp_path,
            offline=True,
            breaking_changes=True,
        )

    registry.assert_not_called()
    osv.assert_not_called()
    comparator.assert_not_called()

    assert (
        report["dependencies"][0]["api_analysis_status"]
        == "offline"
    )


def test_github_api_analysis():

    def fake_clone(url, destination):

        destination.mkdir()

        (destination / "requirements.txt").write_text(
            "requests==2.28.0\n",
            encoding="utf-8",
        )

        return destination

    with patch(
        "codedrift.repository.analyzer.clone_repository",
        side_effect=fake_clone,
    ), patch(
        REGISTRY,
        return_value="2.32.0",
    ), patch(
        OSV,
        return_value=[],
    ), patch(
        COMPARATOR,
        return_value={
            "comparison_status": "completed",
            "breaking_count": 1,
            "changes": [],
        },
    ) as comparator:

        report = analyze_github_repository(
            "https://github.com/owner/demo",
            breaking_changes=True,
            max_comparisons=1,
        )

    comparator.assert_called_once()

    assert report["repository"] == "demo"

    assert report["api_analysis"]["max_comparisons"] == 1

    assert (
        report["api_analysis"]["unique_comparisons_completed"]
        == 1
    )
