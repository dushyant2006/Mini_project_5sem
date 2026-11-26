
import json
import re
from pathlib import Path

from codedrift.dependency.registry_client import (
    extract_exact_version,
)


MAX_LOCKFILE_BYTES = 10_000_000

NPM_GROUPS = {
    "runtime": "dependencies",
    "dev": "devDependencies",
    "development": "devDependencies",
    "optional": "optionalDependencies",
    "peer": "peerDependencies",
}


def get_npm_locked_version(dependency, repository_path):

    root = Path(repository_path).resolve()

    manifest = (
        root / dependency["source"]
    ).resolve()

    if not manifest.is_relative_to(root):
        return None

    lockfile = manifest.parent / "package-lock.json"

    if not lockfile.is_file() or lockfile.is_symlink():
        return None

    if (manifest.parent / "npm-shrinkwrap.json").exists():
        return None

    try:

        if lockfile.stat().st_size > MAX_LOCKFILE_BYTES:
            return None

        data = json.loads(
            lockfile.read_text(encoding="utf-8-sig")
        )

        if data.get("lockfileVersion") not in (2, 3):
            return None

        packages = data.get("packages", {})

        root_package = packages.get("", {})

        group = NPM_GROUPS.get(
            dependency["group"]
        )

        if group is None:
            return None

        name = dependency["name"]

        constraint = dependency["constraint"]

        if not re.fullmatch(
            r"(?:@[A-Za-z0-9_.-]+/)?[A-Za-z0-9][A-Za-z0-9_.-]*",
            name,
        ):
            return None

        if not re.fullmatch(
            r"[\d.^~<>=*xX| ,+-]+",
            constraint,
        ):
            return None

        declared = root_package.get(
            group, {}
        ).get(name)

        if declared != constraint:
            return None

        package = packages.get(
            f"node_modules/{name}", {}
        )

        if package.get("link"):
            return None

        if package.get("name", name) != name:
            return None

        resolved = package.get("resolved", "")

        if resolved and not resolved.startswith(
            "https://registry.npmjs.org/"
        ):
            return None

        version = package.get("version")

        if not isinstance(version, str):
            return None

        return extract_exact_version(version, "npm")

    except (
        OSError,
        ValueError,
        TypeError,
        AttributeError,
    ):
        return None


def resolve_dependency(dependency, repository_path):

    ecosystem = dependency["ecosystem"]

    constraint = dependency["constraint"]

    baseline = None

    source = "unresolved"

    if ecosystem == "npm":

        baseline = get_npm_locked_version(
            dependency,
            repository_path,
        )

        if baseline is not None:
            source = "package-lock.json"

    if baseline is None:

        baseline = extract_exact_version(
            constraint,
            ecosystem,
        )

        if baseline is not None:
            source = "declared_pin"

    return {
        **dependency,
        "baseline_version": baseline,
        "version_source": source,
    }
