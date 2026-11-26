
import hashlib
import json
import zipfile

import pytest

from unittest.mock import patch

from codedrift.dependency.package_downloader import (
    validate_package,
    get_release_artifact,
    download_package,
    extract_python_sources,
    prepare_package,
    PackageDownloadError,
)


FETCH = (
    "codedrift.dependency.package_downloader.fetch_bytes"
)


ARTIFACT = (
    "codedrift.dependency.package_downloader."
    "get_release_artifact"
)


def test_validate_package():

    name, version = validate_package(
        "Flask",
        "3.1.0",
    )

    assert name == "flask"
    assert version == "3.1.0"


def test_invalid_package_name():

    with pytest.raises(PackageDownloadError):

        validate_package("../flask", "3.1.0")


def test_invalid_package_version():

    with pytest.raises(PackageDownloadError):

        validate_package("flask", "latest")


def test_get_release_artifact():

    metadata = {
        "urls": [
            {
                "filename": "flask-3.1.0.tar.gz",
                "packagetype": "sdist",
            },
            {
                "filename": (
                    "flask-3.1.0-py3-none-any.whl"
                ),
                "packagetype": "bdist_wheel",
                "yanked": False,
            },
        ]
    }

    with patch(
        FETCH,
        return_value=json.dumps(metadata).encode(),
    ):

        result = get_release_artifact(
            "flask",
            "3.1.0",
        )

    assert result["filename"].endswith(".whl")


def test_no_supported_wheel():

    metadata = {
        "urls": [
            {
                "filename": "flask-3.1.0.tar.gz",
                "packagetype": "sdist",
            }
        ]
    }

    with patch(
        FETCH,
        return_value=json.dumps(metadata).encode(),
    ):

        with pytest.raises(PackageDownloadError):

            get_release_artifact("flask", "3.1.0")


def test_download_package(tmp_path):

    content = b"sample package"

    artifact = {
        "filename": "demo-1.0.0-py3-none-any.whl",
        "url": "https://files.pythonhosted.org/demo.whl",
        "size": len(content),
        "digests": {
            "sha256": hashlib.sha256(
                content
            ).hexdigest(),
        },
    }

    with patch(ARTIFACT, return_value=artifact), \
         patch(FETCH, return_value=content):

        result = download_package(
            "demo",
            "1.0.0",
            tmp_path,
        )

    assert result.exists()
    assert result.read_bytes() == content


def test_checksum_mismatch(tmp_path):

    artifact = {
        "filename": "demo-1.0.0-py3-none-any.whl",
        "url": "https://files.pythonhosted.org/demo.whl",
        "digests": {
            "sha256": "0" * 64,
        },
    }

    with patch(ARTIFACT, return_value=artifact), \
         patch(FETCH, return_value=b"invalid"):

        with pytest.raises(
            PackageDownloadError,
            match="checksum",
        ):

            download_package(
                "demo",
                "1.0.0",
                tmp_path,
            )


def test_extract_python_sources(tmp_path):

    archive = tmp_path / "demo.whl"

    with zipfile.ZipFile(archive, "w") as wheel:

        wheel.writestr(
            "demo/__init__.py",
            "def hello(): return 'hello'",
        )

        wheel.writestr(
            "demo/helpers.py",
            "def add(a, b): return a + b",
        )

        wheel.writestr(
            "demo-1.0.0.dist-info/METADATA",
            "Name: demo",
        )

    destination = tmp_path / "sources"

    files = extract_python_sources(
        archive,
        destination,
    )

    assert len(files) == 2

    assert (
        destination / "demo" / "helpers.py"
    ).exists()

    assert not (
        destination / "demo-1.0.0.dist-info"
    ).exists()


def test_unsafe_archive_path(tmp_path):

    archive = tmp_path / "unsafe.whl"

    with zipfile.ZipFile(archive, "w") as wheel:

        wheel.writestr(
            "../outside.py",
            "print('unsafe')",
        )

    with pytest.raises(PackageDownloadError):

        extract_python_sources(
            archive,
            tmp_path / "sources",
        )

    assert not (tmp_path / "outside.py").exists()


def test_empty_python_archive(tmp_path):

    archive = tmp_path / "empty.whl"

    with zipfile.ZipFile(archive, "w") as wheel:

        wheel.writestr("README.txt", "Example")

    with pytest.raises(
        PackageDownloadError,
        match="No Python source",
    ):

        extract_python_sources(
            archive,
            tmp_path / "sources",
        )


def test_prepare_package(tmp_path):

    archive = tmp_path / "demo.whl"

    with zipfile.ZipFile(archive, "w") as wheel:

        wheel.writestr(
            "demo/__init__.py",
            "def hello(): pass",
        )

    with patch(
        "codedrift.dependency.package_downloader."
        "download_package",
        return_value=archive,
    ):

        result = prepare_package(
            "demo",
            "1.0.0",
            tmp_path,
        )

    assert result["name"] == "demo"
    assert result["version"] == "1.0.0"
    assert result["python_file_count"] == 1
