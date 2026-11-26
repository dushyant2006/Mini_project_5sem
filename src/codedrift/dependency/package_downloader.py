
import argparse
import hashlib
import json
import re
import tempfile
import zipfile

from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from packaging.utils import (
    canonicalize_name,
    parse_wheel_filename,
)

from packaging.version import Version, InvalidVersion


MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024

MAX_EXTRACTED_BYTES = 100 * 1024 * 1024

MAX_ARCHIVE_ENTRIES = 10000

REQUEST_TIMEOUT = 30


class PackageDownloadError(Exception):
    pass


def validate_package(name, version):

    if not re.fullmatch(
        r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?",
        name,
    ):
        raise PackageDownloadError("Invalid package name")

    try:

        normalized_version = str(Version(version))

    except InvalidVersion as error:

        raise PackageDownloadError(
            "Invalid package version"
        ) from error

    return canonicalize_name(name), normalized_version


def fetch_bytes(url, limit, allowed_host):

    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or parsed.netloc != allowed_host
    ):
        raise PackageDownloadError("Untrusted download URL")

    request = Request(
        url,
        headers={
            "User-Agent": "CodeDrift/2.0",
        },
    )

    try:

        with urlopen(
            request,
            timeout=REQUEST_TIMEOUT,
        ) as response:

            final_url = urlparse(response.geturl())

            if (
                final_url.scheme != "https"
                or final_url.netloc != allowed_host
            ):
                raise PackageDownloadError(
                    "Unexpected redirect destination"
                )

            data = response.read(limit + 1)

    except OSError as error:

        raise PackageDownloadError(
            f"Download failed: {error}"
        ) from error

    if len(data) > limit:

        raise PackageDownloadError(
            "Download size limit exceeded"
        )

    return data


def get_release_artifact(name, version):

    name, version = validate_package(name, version)

    url = (
        f"https://pypi.org/pypi/"
        f"{quote(name, safe='')}/"
        f"{quote(version, safe='')}/json"
    )

    raw = fetch_bytes(
        url,
        10 * 1024 * 1024,
        "pypi.org",
    )

    try:

        metadata = json.loads(raw)

    except ValueError as error:

        raise PackageDownloadError(
            "Invalid PyPI metadata"
        ) from error

    candidates = []

    for artifact in metadata.get("urls", []):

        if artifact.get("packagetype") != "bdist_wheel":
            continue

        if artifact.get("yanked"):
            continue

        filename = artifact.get("filename", "")

        try:

            wheel_name, wheel_version, _, tags = (
                parse_wheel_filename(filename)
            )

        except ValueError:
            continue

        if canonicalize_name(wheel_name) != name:
            continue

        if wheel_version != Version(version):
            continue

        if not all(
            tag.abi == "none"
            and tag.platform == "any"
            for tag in tags
        ):
            continue

        candidates.append(artifact)

    if not candidates:

        raise PackageDownloadError(
            f"No supported pure-Python wheel for "
            f"{name}=={version}"
        )

    candidates.sort(
        key=lambda item: item["filename"]
    )

    return candidates[0]


def download_package(name, version, destination):

    destination = Path(destination)

    artifact = get_release_artifact(name, version)

    filename = artifact["filename"]

    if (
        Path(filename).name != filename
        or "\\" in filename
        or ":" in filename
    ):
        raise PackageDownloadError(
            "Unsafe artifact filename"
        )

    expected_hash = artifact.get(
        "digests", {}
    ).get("sha256")

    if not expected_hash or not re.fullmatch(
        r"[a-fA-F0-9]{64}",
        expected_hash,
    ):
        raise PackageDownloadError(
            "Missing or invalid SHA-256 checksum"
        )

    if artifact.get("size", 0) > MAX_DOWNLOAD_BYTES:

        raise PackageDownloadError(
            "Package exceeds download limit"
        )

    data = fetch_bytes(
        artifact["url"],
        MAX_DOWNLOAD_BYTES,
        "files.pythonhosted.org",
    )

    actual_hash = hashlib.sha256(data).hexdigest()

    if actual_hash != expected_hash.lower():

        raise PackageDownloadError(
            "Package checksum verification failed"
        )

    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    package_path = destination / filename

    with package_path.open("xb") as file:

        file.write(data)

    return package_path


def extract_python_sources(archive_path, destination):

    destination = Path(destination)

    if destination.exists():

        raise PackageDownloadError(
            "Extraction destination must not exist"
        )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    extracted_files = []

    try:

        with tempfile.TemporaryDirectory(
            dir=destination.parent
        ) as workspace:

            root = Path(workspace) / "sources"

            root.mkdir()

            with zipfile.ZipFile(archive_path) as archive:

                entries = archive.infolist()

                if len(entries) > MAX_ARCHIVE_ENTRIES:

                    raise PackageDownloadError(
                        "Too many archive entries"
                    )

                total_size = sum(
                    entry.file_size
                    for entry in entries
                )

                if total_size > MAX_EXTRACTED_BYTES:

                    raise PackageDownloadError(
                        "Archive extraction limit exceeded"
                    )

                seen_paths = set()

                for entry in entries:

                    name = entry.filename

                    parts = name.rstrip("/").split("/")

                    if (
                        not parts
                        or any(
                            part in ("", ".", "..")
                            or "\\" in part
                            or ":" in part
                            or part.endswith((" ", "."))
                            or any(
                                character in '<>"|?*'
                                or ord(character) < 32
                                for character in part
                            )
                            or re.fullmatch(
                                r"(?i)(CON|PRN|AUX|NUL|"
                                r"COM[1-9¹²³]|LPT[1-9¹²³])",
                                part.split(".")[0],
                            )
                            for part in parts
                        )
                    ):
                        raise PackageDownloadError(
                            "Unsafe archive path"
                        )

                    mode = (
                        entry.external_attr >> 16
                    ) & 0o170000

                    if mode not in (
                        0,
                        0o100000,
                        0o040000,
                    ):
                        raise PackageDownloadError(
                            "Unsupported archive entry type"
                        )

                    if entry.is_dir():
                        continue

                    if not name.endswith(".py"):
                        continue

                    if any(
                        part.endswith(
                            (".dist-info", ".data")
                        )
                        for part in parts[:-1]
                    ):
                        continue

                    relative_path = Path(*parts)

                    key = relative_path.as_posix().casefold()

                    if key in seen_paths:

                        raise PackageDownloadError(
                            "Duplicate archive path"
                        )

                    seen_paths.add(key)

                    output = root / relative_path

                    if not output.resolve().is_relative_to(
                        root.resolve()
                    ):
                        raise PackageDownloadError(
                            "Unsafe extraction destination"
                        )

                    output.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    with archive.open(entry) as source:

                        content = source.read(
                            entry.file_size + 1
                        )

                    if len(content) != entry.file_size:

                        raise PackageDownloadError(
                            "Invalid archive entry size"
                        )

                    with output.open("xb") as file:

                        file.write(content)

                    extracted_files.append(relative_path)

            if not extracted_files:

                raise PackageDownloadError(
                    "No Python source files found"
                )

            root.rename(destination)

    except (
        zipfile.BadZipFile,
        OSError,
        RuntimeError,
        NotImplementedError,
    ) as error:

        raise PackageDownloadError(
            f"Extraction failed: {error}"
        ) from error

    return [
        destination / path
        for path in extracted_files
    ]


def prepare_package(name, version, workspace):

    name, version = validate_package(name, version)

    workspace = Path(workspace)

    package_directory = (
        workspace / f"{name}-{version}"
    )

    package_directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    archive = download_package(
        name,
        version,
        package_directory,
    )

    source_directory = package_directory / "sources"

    files = extract_python_sources(
        archive,
        source_directory,
    )

    return {
        "name": name,
        "version": version,
        "archive": str(archive),
        "source_directory": str(source_directory),
        "python_file_count": len(files),
    }


def main():

    parser = argparse.ArgumentParser(
        description="CodeDrift Python package downloader"
    )

    parser.add_argument("name")
    parser.add_argument("version")
    parser.add_argument("workspace")

    args = parser.parse_args()

    try:

        result = prepare_package(
            args.name,
            args.version,
            args.workspace,
        )

        print(json.dumps(result, indent=2))

    except (PackageDownloadError, OSError) as error:

        parser.exit(
            status=1,
            message=f"CodeDrift error: {error}\n",
        )


if __name__ == "__main__":
    main()
