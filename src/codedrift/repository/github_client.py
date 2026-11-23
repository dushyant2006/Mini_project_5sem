
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse


class RepositoryError(Exception):
    pass


def validate_github_url(url: str) -> str:
    parsed = urlparse(url.strip())

    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.port is not None
        or parsed.username
        or parsed.password
    ):
        raise RepositoryError("Only HTTPS GitHub URLs are supported")

    if parsed.query or parsed.fragment:
        raise RepositoryError("Query parameters are not supported")

    parts = parsed.path.strip("/").split("/")

    if len(parts) != 2:
        raise RepositoryError(
            "Expected https://github.com/owner/repository"
        )

    owner, repo = parts
    repo = repo.removesuffix(".git")

    pattern = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}"

    if not re.fullmatch(pattern, owner):
        raise RepositoryError("Invalid GitHub owner")

    if not re.fullmatch(pattern, repo):
        raise RepositoryError("Invalid repository name")

    return f"https://github.com/{owner}/{repo}.git"


def clone_repository(url: str, destination: str | Path) -> Path:
    safe_url = validate_github_url(url)
    destination = Path(destination).resolve()

    if destination.exists():
        raise RepositoryError("Destination already exists")

    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GIT_LFS_SKIP_SMUDGE"] = "1"

    try:
        subprocess.run(
            [
                "git",
                "-c", "protocol.file.allow=never",
                "clone",
                "--depth", "1",
                "--single-branch",
                "--no-tags",
                safe_url,
                str(destination),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
            env=environment,
        )
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ) as error:
        shutil.rmtree(destination, ignore_errors=True)
        raise RepositoryError(
            f"Unable to clone repository: {type(error).__name__}"
        ) from error

    return destination
