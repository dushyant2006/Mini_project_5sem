
import json
import os
import re
from pathlib import Path


MANIFEST_TYPES = {
    "pyproject.toml": ("python", "pypi"),
    "Pipfile": ("python", "pypi"),
    "package.json": ("javascript", "npm"),
    "pom.xml": ("java", "maven"),
}

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".next",
    "dist",
    "build",
    "target",
    ".tox",
}


def identify_manifest(path: Path):
    name = path.name

    if name in MANIFEST_TYPES:
        return MANIFEST_TYPES[name]

    if re.fullmatch(
        r"requirements(?:[-_][\w-]+)?\.txt",
        name,
        flags=re.IGNORECASE,
    ):
        return ("python", "pypi")

    if (
        path.parent.name == "requirements"
        and name.endswith(".txt")
    ):
        return ("python", "pypi")

    return None


def scan_manifests(repository_path):
    root = Path(repository_path).resolve()

    if not root.is_dir():
        raise ValueError(
            f"Repository directory does not exist: {root}"
        )

    manifests = []

    for current_dir, dirs, files in os.walk(
        root, followlinks=False
    ):
        dirs[:] = sorted(
            directory
            for directory in dirs
            if directory not in IGNORED_DIRECTORIES
            and not (Path(current_dir) / directory).is_symlink()
        )

        for filename in sorted(files):
            path = Path(current_dir) / filename

            if path.is_symlink():
                continue

            result = identify_manifest(path)

            if result is None:
                continue

            language, ecosystem = result

            manifests.append({
                "path": path.relative_to(root).as_posix(),
                "filename": filename,
                "language": language,
                "ecosystem": ecosystem,
            })

    return sorted(
        manifests,
        key=lambda item: item["path"]
    )


def analyze_repository_structure(repository_path):
    root = Path(repository_path).resolve()

    manifests = scan_manifests(root)

    return {
        "repository": root.name,
        "supported_manifests": len(manifests),
        "languages": sorted({
            item["language"] for item in manifests
        }),
        "ecosystems": sorted({
            item["ecosystem"] for item in manifests
        }),
        "manifests": manifests,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(
            "Usage: python -m "
            "codedrift.dependency.manifest_scanner "
            "<repository_path>"
        )
        raise SystemExit(1)

    try:
        report = analyze_repository_structure(sys.argv[1])
    except ValueError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)

    print(json.dumps(report, indent=2))
