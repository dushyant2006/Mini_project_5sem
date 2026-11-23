
from unittest.mock import patch

import pytest

from codedrift.repository.github_client import (
    RepositoryError,
    clone_repository,
    validate_github_url,
)


def test_valid_url():
    assert validate_github_url(
        "https://github.com/pallets/flask"
    ) == "https://github.com/pallets/flask.git"


def test_invalid_domain():
    with pytest.raises(RepositoryError):
        validate_github_url(
            "https://example.com/owner/repo"
        )


def test_nested_path():
    with pytest.raises(RepositoryError):
        validate_github_url(
            "https://github.com/owner/repo/tree/main"
        )


def test_clone_repository(tmp_path):
    destination = tmp_path / "sample"

    def fake_clone(command, **kwargs):
        destination.mkdir()
        (destination / "requirements.txt").write_text(
            "requests==2.28.0"
        )

    with patch(
        "codedrift.repository.github_client.subprocess.run",
        side_effect=fake_clone
    ):
        path = clone_repository(
            "https://github.com/owner/sample",
            destination
        )

    assert path.exists()
    assert (path / "requirements.txt").exists()
