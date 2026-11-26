
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastapi.testclient import TestClient

from codedrift.api.v2_server import create_app
from codedrift.api.scan_store import ScanStore


ANALYZER = (
    "codedrift.api.v2_server."
    "analyze_full_github_repository"
)


SAMPLE_REPORT = {
    "repository": "demo",
    "dependency_count": 2,
    "updates_found": 1,
    "vulnerable_dependencies": 1,
    "vulnerabilities_found": 1,
    "unique_advisory_count": 1,
    "unique_cve_count": 1,
    "unique_cve_ids": ["CVE-2099-0001"],
    "security_checked": 2,
    "security_unchecked": 0,
    "security_lookup_failures": 0,
    "api_analysis": {
        "unique_comparisons_completed": 1,
    },
    "impact_analysis": {
        "highest_dependency_impact_score": 65.0,
        "coverage_limited": True,
    },
    "dependencies": [
        {
            "name": "paymentlib",
            "ecosystem": "pypi",
            "baseline_version": "1.0.0",
            "latest_release": "2.0.0",
            "comparison_status": "update_available",
            "security_status": "vulnerable",
            "vulnerability_count": 1,
            "vulnerabilities": [
                {
                    "id": "TEST-001",
                    "cve_ids": ["CVE-2099-0001"],
                }
            ],
            "api_analysis_status": "completed",
            "api_breaking_count": 2,
            "api_comparison": {
                "comparison_status": "completed",
                "breaking_count": 2,
                "changes": [],
            },
            "impact_analysis_status": "completed",
            "impact_score": 65.0,
            "risk_level": "HIGH",
            "impact_report": {
                "total_findings": 2,
            },
        },
        {
            "name": "axios",
            "ecosystem": "npm",
            "baseline_version": "1.0.0",
            "latest_release": "1.0.0",
            "comparison_status": "up_to_date",
            "security_status": "no_known_vulnerabilities",
            "vulnerability_count": 0,
            "vulnerabilities": [],
            "risk_level": "UNKNOWN",
        },
    ],
}


@pytest.fixture
def client(tmp_path):

    app = create_app(
        tmp_path / "scans"
    )

    with TestClient(app) as test_client:

        yield test_client


@pytest.fixture
def completed_scan(client):

    with patch(
        ANALYZER,
        return_value=SAMPLE_REPORT,
    ):

        response = client.post(
            "/api/v2/analyze",
            json={
                "repository_url": (
                    "https://github.com/owner/demo"
                ),
            },
        )

    assert response.status_code == 202

    return response.json()["scan_id"]


def test_root(client):

    response = client.get("/")

    assert response.status_code == 200

    assert response.json()["service"] == "CodeDrift"


def test_health(client):

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json()["status"] == "healthy"


def test_versioned_health(client):

    response = client.get("/api/v2/health")

    assert response.status_code == 200


def test_swagger_documentation(client):

    response = client.get("/docs")

    assert response.status_code == 200


def test_openapi_schema(client):

    response = client.get("/openapi.json")

    assert response.status_code == 200

    assert "/api/v2/analyze" in response.json()["paths"]


def test_start_scan(client):

    with patch(
        ANALYZER,
        return_value=SAMPLE_REPORT,
    ):

        response = client.post(
            "/api/v2/analyze",
            json={
                "repository_url": (
                    "https://github.com/owner/demo"
                ),
            },
        )

    assert response.status_code == 202

    assert response.json()["status"] == "queued"

    assert response.json()["scan_id"]


def test_completed_scan(client, completed_scan):

    response = client.get(
        f"/api/v2/scans/{completed_scan}"
    )

    assert response.status_code == 200

    assert response.json()["status"] == "completed"

    assert response.json()["report"][
        "dependency_count"
    ] == 2


def test_invalid_repository_url(client):

    response = client.post(
        "/api/v2/analyze",
        json={
            "repository_url": (
                "https://example.com/owner/demo"
            ),
        },
    )

    assert response.status_code == 422


def test_negative_comparison_limit(client):

    response = client.post(
        "/api/v2/analyze",
        json={
            "repository_url": (
                "https://github.com/owner/demo"
            ),
            "max_comparisons": -1,
        },
    )

    assert response.status_code == 422


def test_excessive_comparison_limit(client):

    response = client.post(
        "/api/v2/analyze",
        json={
            "repository_url": (
                "https://github.com/owner/demo"
            ),
            "max_comparisons": 100,
        },
    )

    assert response.status_code == 422


def test_missing_repository_url(client):

    response = client.post(
        "/api/v2/analyze",
        json={},
    )

    assert response.status_code == 422


def test_scan_not_found(client):

    response = client.get(
        f"/api/v2/scans/{uuid4()}"
    )

    assert response.status_code == 404


def test_invalid_scan_id(client):

    response = client.get(
        "/api/v2/scans/invalid-id"
    )

    assert response.status_code == 422


def test_scan_history(client, completed_scan):

    response = client.get("/api/v2/scans")

    data = response.json()

    assert response.status_code == 200

    assert data["total"] == 1

    assert data["scans"][0]["id"] == completed_scan

    assert "report" not in data["scans"][0]


def test_empty_scan_history(client):

    response = client.get("/api/v2/scans")

    assert response.json()["total"] == 0


def test_scan_pagination(client, completed_scan):

    response = client.get(
        "/api/v2/scans?limit=1&offset=1"
    )

    assert response.json()["total"] == 1

    assert response.json()["scans"] == []


def test_dependencies(client, completed_scan):

    response = client.get(
        f"/api/v2/scans/{completed_scan}/dependencies"
    )

    assert response.status_code == 200

    assert response.json()["dependency_count"] == 2


def test_ecosystem_filter(client, completed_scan):

    response = client.get(
        f"/api/v2/scans/{completed_scan}"
        "/dependencies?ecosystem=npm"
    )

    assert response.json()["dependency_count"] == 1

    assert response.json()["dependencies"][0][
        "name"
    ] == "axios"


def test_updates_filter(client, completed_scan):

    response = client.get(
        f"/api/v2/scans/{completed_scan}"
        "/dependencies?updates_only=true"
    )

    assert response.json()["dependency_count"] == 1


def test_security_report(client, completed_scan):

    response = client.get(
        f"/api/v2/scans/{completed_scan}/security"
    )

    assert response.status_code == 200

    assert response.json()["unique_cve_count"] == 1

    assert len(
        response.json()["dependencies"]
    ) == 1


def test_breaking_changes(client, completed_scan):

    response = client.get(
        f"/api/v2/scans/{completed_scan}"
        "/breaking-changes"
    )

    assert response.status_code == 200

    assert response.json()["comparisons"][0][
        "breaking_count"
    ] == 2


def test_impact_report(client, completed_scan):

    response = client.get(
        f"/api/v2/scans/{completed_scan}/impact"
    )

    assert response.status_code == 200

    assert response.json()["dependencies"][0][
        "risk_level"
    ] == "HIGH"


def test_delete_scan(client, completed_scan):

    response = client.delete(
        f"/api/v2/scans/{completed_scan}"
    )

    assert response.status_code == 200

    assert response.json()["deleted"]

    response = client.get(
        f"/api/v2/scans/{completed_scan}"
    )

    assert response.status_code == 404


def test_delete_missing_scan(client):

    response = client.delete(
        f"/api/v2/scans/{uuid4()}"
    )

    assert response.status_code == 404


def test_failed_analysis(client):

    with patch(
        ANALYZER,
        side_effect=RuntimeError("Test failure"),
    ):

        response = client.post(
            "/api/v2/analyze",
            json={
                "repository_url": (
                    "https://github.com/owner/demo"
                ),
            },
        )

    scan_id = response.json()["scan_id"]

    result = client.get(
        f"/api/v2/scans/{scan_id}"
    )

    assert result.json()["status"] == "failed"

    assert result.json()["error"]


def test_incomplete_scan_report(client):

    store = client.app.state.scan_store

    record = store.create(
        "https://github.com/owner/demo"
    )

    response = client.get(
        f"/api/v2/scans/{record['id']}/dependencies"
    )

    assert response.status_code == 409


def test_active_scan_cannot_be_deleted(client):

    store = client.app.state.scan_store

    record = store.create(
        "https://github.com/owner/demo"
    )

    response = client.delete(
        f"/api/v2/scans/{record['id']}"
    )

    assert response.status_code == 409


def test_active_scan_limit(client):

    store = client.app.state.scan_store

    store.create(
        "https://github.com/owner/demo1"
    )

    store.create(
        "https://github.com/owner/demo2"
    )

    response = client.post(
        "/api/v2/analyze",
        json={
            "repository_url": (
                "https://github.com/owner/demo3"
            ),
        },
    )

    assert response.status_code == 429


def test_offline_option(client):

    with patch(
        ANALYZER,
        return_value=SAMPLE_REPORT,
    ) as analyzer:

        response = client.post(
            "/api/v2/analyze",
            json={
                "repository_url": (
                    "https://github.com/owner/demo"
                ),
                "offline": True,
                "max_comparisons": 2,
            },
        )

    assert response.status_code == 202

    assert analyzer.call_args.kwargs["offline"]

    assert analyzer.call_args.kwargs[
        "max_comparisons"
    ] == 2


def test_storage_persistence(tmp_path):

    directory = tmp_path / "scans"

    store = ScanStore(directory)

    record = store.create(
        "https://github.com/owner/demo"
    )

    another_store = ScanStore(directory)

    saved = another_store.get(record["id"])

    assert saved["id"] == record["id"]


def test_interrupted_scan_recovery(tmp_path):

    store = ScanStore(tmp_path)

    record = store.create(
        "https://github.com/owner/demo"
    )

    store.update(
        record["id"],
        status="running",
    )

    store.recover_interrupted_scans()

    recovered = store.get(record["id"])

    assert recovered["status"] == "failed"


def test_storage_path_validation(tmp_path):

    store = ScanStore(tmp_path)

    with pytest.raises(ValueError):

        store.get("../../secret")


def test_cors(client):

    response = client.options(
        "/api/v2/analyze",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200

    assert response.headers[
        "access-control-allow-origin"
    ] == "http://localhost:5173"
