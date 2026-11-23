
import json
import re
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

from packaging.requirements import Requirement

from codedrift.dependency.manifest_scanner import (
    identify_manifest,
    scan_manifests,
)


MAX_MANIFEST_BYTES = 2_000_000


def make_dependency(
    name,
    ecosystem,
    constraint,
    source,
    group="runtime",
):
    constraint = str(constraint).strip()

    return {
        "name": name,
        "ecosystem": ecosystem,
        "constraint": constraint,
        "source": source,
        "group": group,
    }


def parse_requirements(content, source):
    dependencies = []
    warnings = []

    for line_number, raw_line in enumerate(
        content.splitlines(), start=1
    ):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith(("-", "git+", "http://", "https://")):
            warnings.append(
                f"{source}:{line_number}: "
                "unsupported requirement directive or URL"
            )
            continue

        line = re.split(r"\s+#", line, maxsplit=1)[0]

        try:
            requirement = Requirement(line)
        except ValueError:
            warnings.append(
                f"{source}:{line_number}: "
                "could not parse requirement"
            )
            continue

        if requirement.url:
            warnings.append(
                f"{source}:{line_number}: "
                "direct URL requirement is not supported"
            )
            continue

        dependencies.append(
            make_dependency(
                requirement.name,
                "pypi",
                str(requirement.specifier),
                source,
            )
        )

    return dependencies, warnings


def parse_pyproject(content, source):
    data = tomllib.loads(content)
    dependencies = []
    warnings = []

    project = data.get("project", {})

    def add_requirements(items, group):
        for value in items:
            try:
                requirement = Requirement(value)

                if requirement.url:
                    warnings.append(
                        f"{source}: direct URL not supported: "
                        f"{requirement.name}"
                    )
                    continue

                dependencies.append(
                    make_dependency(
                        requirement.name,
                        "pypi",
                        str(requirement.specifier),
                        source,
                        group,
                    )
                )

            except ValueError:
                warnings.append(
                    f"{source}: unsupported requirement: {value}"
                )

    add_requirements(
        project.get("dependencies", []),
        "runtime",
    )

    for group, items in project.get(
        "optional-dependencies", {}
    ).items():
        add_requirements(items, group)

    if "dependencies" in project.get("dynamic", []):
        warnings.append(
            f"{source}: dynamic dependencies need "
            "build-backend resolution"
        )

    if "poetry" in data.get("tool", {}):
        warnings.append(
            f"{source}: Poetry-specific dependencies "
            "are not parsed yet"
        )

    return dependencies, warnings


def parse_package_json(content, source):
    data = json.loads(content)
    dependencies = []
    warnings = []

    sections = {
        "dependencies": "runtime",
        "devDependencies": "development",
        "optionalDependencies": "optional",
        "peerDependencies": "peer",
    }

    for section, group in sections.items():
        for name, constraint in data.get(
            section, {}
        ).items():
            if not isinstance(constraint, str):
                warnings.append(
                    f"{source}: invalid version for {name}"
                )
                continue

            dependencies.append(
                make_dependency(
                    name,
                    "npm",
                    constraint,
                    source,
                    group,
                )
            )

    return dependencies, warnings


def parse_pom_xml(content, source):
    root = ET.fromstring(content)
    dependencies = []
    warnings = []

    properties = {}

    properties_node = root.find("./{*}properties")

    if properties_node is not None:
        for child in properties_node:
            key = child.tag.split("}")[-1]
            properties[key] = (child.text or "").strip()

    version_node = root.find("./{*}version")

    if version_node is not None:
        properties["project.version"] = (
            version_node.text or ""
        ).strip()

    for item in root.findall(
        "./{*}dependencies/{*}dependency"
    ):
        def get_text(name):
            node = item.find(f"./{{*}}{name}")
            return (
                (node.text or "").strip()
                if node is not None
                else ""
            )

        group_id = get_text("groupId")
        artifact_id = get_text("artifactId")
        version = get_text("version")
        scope = get_text("scope") or "compile"

        if not group_id or not artifact_id:
            warnings.append(
                f"{source}: dependency missing coordinates"
            )
            continue

        if version.startswith("${") and version.endswith("}"):
            key = version[2:-1]
            version = properties.get(key, version)

        if not version:
            warnings.append(
                f"{source}: {group_id}:{artifact_id} "
                "has no explicit version; it may be managed"
            )

        if "${" in version:
            warnings.append(
                f"{source}: unresolved version for "
                f"{group_id}:{artifact_id}"
            )

        dependencies.append(
            make_dependency(
                f"{group_id}:{artifact_id}",
                "maven",
                version,
                source,
                scope,
            )
        )

    return dependencies, warnings


def parse_manifest(path, root):
    path = Path(path).resolve()
    root = Path(root).resolve()

    if not path.is_relative_to(root):
        raise ValueError("Manifest is outside repository")

    if path.is_symlink() or not path.is_file():
        raise ValueError("Manifest must be a regular file")

    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Manifest exceeds size limit")

    source = path.relative_to(root).as_posix()
    content = path.read_text(encoding="utf-8-sig")

    if path.name == "package.json":
        return parse_package_json(content, source)

    if path.name == "pom.xml":
        return parse_pom_xml(content, source)

    if path.name == "pyproject.toml":
        return parse_pyproject(content, source)

    if path.name.lower().endswith(".txt"):
        return parse_requirements(content, source)

    return [], [
        f"{source}: format not supported by parser"
    ]


def extract_dependencies(repository_path):
    root = Path(repository_path).resolve()

    dependencies = []
    warnings = []

    for manifest in scan_manifests(root):
        path = root / manifest["path"]

        try:
            parsed, issues = parse_manifest(path, root)
            dependencies.extend(parsed)
            warnings.extend(issues)

        except (
            ValueError,
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ET.ParseError,
        ) as error:
            warnings.append(
                f"{manifest['path']}: "
                f"parsing failed: {type(error).__name__}"
            )

    return {
        "repository": root.name,
        "dependency_count": len(dependencies),
        "dependencies": dependencies,
        "warnings": warnings,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(
            "Usage: python -m "
            "codedrift.dependency.manifest_parser "
            "<repository_path>"
        )
        raise SystemExit(1)

    result = extract_dependencies(sys.argv[1])
    print(json.dumps(result, indent=2))
