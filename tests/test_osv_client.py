
import json

from unittest.mock import patch, MagicMock

from codedrift.security.osv_client import (
    fetch_vulnerabilities,
    normalize_vulnerability,
    scan_dependency,
    OSVError,
)


DEPENDENCY = {
    "name": "jinja2",
    "ecosystem": "pypi",
    "baseline_version": "3.1.2",
}


SAMPLE_VULNERABILITY = {
    "id": "TEST-001",
    "summary": "Sample security vulnerability",
    "aliases": ["CVE-2099-0001"],
    "severity": [
        {
            "type": "CVSS_V3",
            "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        }
    ],
    "affected": [
        {
            "package": {
                "name": "jinja2",
                "ecosystem": "PyPI",
            },
            "ranges": [
                {
                    "type": "ECOSYSTEM",
                    "events": [
                        {"introduced": "0"},
                        {"fixed": "3.1.4"},
                    ],
                }
            ],
        }
    ],
}


def test_fetch_vulnerabilities():

    response = MagicMock()

    response.__enter__.return_value.read.return_value = (
        json.dumps({
            "vulns": [SAMPLE_VULNERABILITY]
        }).encode("utf-8")
    )

    with patch(
        "codedrift.security.osv_client.urlopen",
        return_value=response,
    ):

        result = fetch_vulnerabilities(
            "jinja2",
            "3.1.2",
            "pypi",
        )

    assert len(result) == 1


def test_normalize_vulnerability():

    result = normalize_vulnerability(
        SAMPLE_VULNERABILITY,
        "jinja2",
        "pypi",
    )

    assert result["id"] == "TEST-001"

    assert result["fixed_versions"] == ["3.1.4"]

    assert result["cve_ids"] == ["CVE-2099-0001"]


def test_vulnerable_dependency():

    with patch(
        "codedrift.security.osv_client.fetch_vulnerabilities",
        return_value=[SAMPLE_VULNERABILITY],
    ):

        result = scan_dependency(DEPENDENCY)

    assert result["security_status"] == "vulnerable"

    assert result["vulnerability_count"] == 1


def test_no_known_vulnerabilities():

    with patch(
        "codedrift.security.osv_client.fetch_vulnerabilities",
        return_value=[],
    ):

        result = scan_dependency(DEPENDENCY)

    assert result["security_status"] == "no_known_vulnerabilities"

    assert result["vulnerability_count"] == 0


def test_unresolved_version():

    dependency = {
        **DEPENDENCY,
        "baseline_version": None,
    }

    result = scan_dependency(dependency)

    assert result["security_status"] == "unresolved_version"

    assert result["vulnerability_count"] is None


def test_api_failure():

    with patch(
        "codedrift.security.osv_client.fetch_vulnerabilities",
        side_effect=OSVError("Network failure"),
    ):

        result = scan_dependency(DEPENDENCY)

    assert result["security_status"] == "lookup_failed"

    assert result["vulnerability_count"] is None


def test_withdrawn_vulnerability():

    record = {
        **SAMPLE_VULNERABILITY,
        "withdrawn": "2025-01-01T00:00:00Z",
    }

    with patch(
        "codedrift.security.osv_client.fetch_vulnerabilities",
        return_value=[record],
    ):

        result = scan_dependency(DEPENDENCY)

    assert result["vulnerability_count"] == 0


def test_unsupported_ecosystem():

    dependency = {
        **DEPENDENCY,
        "ecosystem": "unknown",
    }

    result = scan_dependency(dependency)

    assert result["security_status"] == "unsupported_ecosystem"
