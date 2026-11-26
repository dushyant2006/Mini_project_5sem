
from unittest.mock import patch

from codedrift.dependency.registry_client import (
    get_latest_release,
    extract_exact_version,
    compare_versions,
    check_dependency,
    check_repository_updates,
)


def test_pypi_release_lookup():

    response = '{"info":{"version":"3.1.0"}}'

    with patch(
        "codedrift.dependency.registry_client.fetch_text",
        return_value=response,
    ):

        version = get_latest_release(
            "flask", "pypi"
        )

    assert version == "3.1.0"


def test_npm_release_lookup():

    response = '{"dist-tags":{"latest":"19.0.0"}}'

    with patch(
        "codedrift.dependency.registry_client.fetch_text",
        return_value=response,
    ):

        version = get_latest_release(
            "react", "npm"
        )

    assert version == "19.0.0"


def test_maven_release_lookup():

    response = """
    <metadata>
        <versioning>
            <release>5.11.0</release>
        </versioning>
    </metadata>
    """

    with patch(
        "codedrift.dependency.registry_client.fetch_text",
        return_value=response,
    ):

        version = get_latest_release(
            "org.junit.jupiter:junit-jupiter",
            "maven",
        )

    assert version == "5.11.0"


def test_exact_version_extraction():

    assert extract_exact_version(
        "==2.28.0", "pypi"
    ) == "2.28.0"

    assert extract_exact_version(
        ">=2.28.0", "pypi"
    ) is None

    assert extract_exact_version(
        "^18.2.0", "npm"
    ) is None

    assert extract_exact_version(
        "==2.28.*", "pypi"
    ) is None


def test_version_comparison():

    assert compare_versions(
        "2.28.0", "2.31.0", "pypi"
    ) == "update_available"

    assert compare_versions(
        "18.2.0", "18.2.0", "npm"
    ) == "up_to_date"

    assert compare_versions(
        "5.10.0", "5.11.0", "maven"
    ) == "comparison_not_supported"


def test_dependency_update_available():

    dependency = {
        "name": "flask",
        "ecosystem": "pypi",
        "constraint": "==2.2.0",
        "source": "requirements.txt",
        "group": "runtime",
    }

    with patch(
        "codedrift.dependency.registry_client.get_latest_release",
        return_value="3.1.0",
    ):

        result = check_dependency(dependency)

    assert result["comparison_status"] == "update_available"
    assert result["latest_release"] == "3.1.0"


def test_version_range_requires_resolution():

    dependency = {
        "name": "rich",
        "ecosystem": "pypi",
        "constraint": ">=13.0.0",
        "source": "pyproject.toml",
        "group": "runtime",
    }

    with patch(
        "codedrift.dependency.registry_client.get_latest_release",
        return_value="14.0.0",
    ):

        result = check_dependency(dependency)

    assert result["latest_release"] == "14.0.0"

    assert result["comparison_status"] == (
        "version_resolution_required"
    )


def test_complete_update_scan(tmp_path):

    (tmp_path / "requirements.txt").write_text(
        "flask==2.2.0\n",
        encoding="utf-8",
    )

    with patch(
        "codedrift.dependency.registry_client.get_latest_release",
        return_value="3.1.0",
    ):

        report = check_repository_updates(tmp_path)

    assert report["dependency_count"] == 1
    assert report["updates_found"] == 1
    assert report["dependencies"][0]["name"] == "flask"
