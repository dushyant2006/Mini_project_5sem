
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from urllib.parse import quote
from packaging.version import Version, InvalidVersion

from codedrift.dependency.manifest_parser import (
    extract_dependencies,
)


MAX_RESPONSE_BYTES = 10_000_000


class RegistryError(Exception):
    pass


def fetch_text(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CodeDrift/2.0",
            "Accept": (
                "application/vnd.npm.install-v1+json, "
                "application/json, application/xml"
            ),
        },
    )

    try:
        with urllib.request.urlopen(
            request, timeout=15
        ) as response:

            data = response.read(MAX_RESPONSE_BYTES + 1)

            if len(data) > MAX_RESPONSE_BYTES:
                raise RegistryError(
                    "Registry response exceeds size limit"
                )

            return data.decode("utf-8")

    except (urllib.error.URLError, TimeoutError) as error:
        raise RegistryError(
            f"Registry request failed: {error}"
        ) from error


def get_latest_release(name, ecosystem):

    if ecosystem == "pypi":

        if not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]*", name
        ):
            raise RegistryError("Invalid Python package name")

        url = (
            "https://pypi.org/pypi/"
            + quote(name, safe="")
            + "/json"
        )

        data = json.loads(fetch_text(url))
        latest = data["info"]["version"]

    elif ecosystem == "npm":

        if not re.fullmatch(
            r"(?:@[A-Za-z0-9_.-]+/)?[A-Za-z0-9][A-Za-z0-9_.-]*",
            name,
        ):
            raise RegistryError("Invalid npm package name")

        url = (
            "https://registry.npmjs.org/"
            + quote(name, safe="")
        )

        data = json.loads(fetch_text(url))
        latest = data["dist-tags"]["latest"]

    elif ecosystem == "maven":

        if ":" not in name:
            raise RegistryError(
                "Maven package requires group:artifact"
            )

        group, artifact = name.split(":", 1)

        if not re.fullmatch(
            r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*",
            group,
        ):
            raise RegistryError("Invalid Maven group")

        if not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]*",
            artifact,
        ):
            raise RegistryError("Invalid Maven artifact")

        group_path = group.replace(".", "/")

        url = (
            "https://repo.maven.apache.org/maven2/"
            f"{group_path}/{artifact}/maven-metadata.xml"
        )

        root = ET.fromstring(fetch_text(url))

        latest = root.findtext(
            "./versioning/release"
        )

        if not latest:
            raise RegistryError(
                "No Maven release version found"
            )

    else:
        raise RegistryError(
            f"Unsupported ecosystem: {ecosystem}"
        )

    if not isinstance(latest, str) or not latest.strip():
        raise RegistryError("Missing release version")

    return latest.strip()


def extract_exact_version(constraint, ecosystem):

    constraint = constraint.strip()

    if ecosystem == "pypi":

        if not constraint.startswith("=="):
            return None

        value = constraint[2:].strip()

        try:
            Version(value)
            return value

        except InvalidVersion:
            return None

    if ecosystem == "npm":

        if re.fullmatch(
            r"\d+\.\d+\.\d+", constraint
        ):
            return constraint

        return None

    if ecosystem == "maven":

        if re.fullmatch(
            r"\d+(?:\.\d+)*", constraint
        ):
            return constraint

        return None

    return None


def compare_versions(current, latest, ecosystem):

    if ecosystem == "maven":
        return "comparison_not_supported"

    if ecosystem == "npm":

        pattern = r"\d+\.\d+\.\d+"

        if not (
            re.fullmatch(pattern, current)
            and re.fullmatch(pattern, latest)
        ):
            return "comparison_not_supported"

        current_parts = tuple(
            map(int, current.split("."))
        )

        latest_parts = tuple(
            map(int, latest.split("."))
        )

        if current_parts < latest_parts:
            return "update_available"

        if current_parts == latest_parts:
            return "up_to_date"

        return "declared_version_newer"

    if ecosystem == "pypi":

        try:
            current_version = Version(current)
            latest_version = Version(latest)

        except InvalidVersion:
            return "comparison_not_supported"

        if current_version < latest_version:
            return "update_available"

        if current_version == latest_version:
            return "up_to_date"

        return "declared_version_newer"

    return "comparison_not_supported"


def check_dependency(dependency):

    name = dependency["name"]
    ecosystem = dependency["ecosystem"]
    constraint = dependency["constraint"]

    result = {
        **dependency,
        "latest_release": None,
        "comparison_status": "not_checked",
        "error": None,
    }

    try:
        latest = get_latest_release(
            name,
            ecosystem,
        )

        result["latest_release"] = latest

        exact = extract_exact_version(
            constraint,
            ecosystem,
        )

        if exact is None:

            result["comparison_status"] = (
                "version_resolution_required"
            )

        else:

            result["comparison_status"] = compare_versions(
                exact,
                latest,
                ecosystem,
            )

    except (
        RegistryError,
        ValueError,
        KeyError,
        TypeError,
        ET.ParseError,
    ) as error:

        result["comparison_status"] = "lookup_failed"
        result["error"] = str(error)

    return result


def check_repository_updates(repository_path):

    report = extract_dependencies(repository_path)

    results = [
        check_dependency(dependency)
        for dependency in report["dependencies"]
    ]

    return {
        "repository": report["repository"],
        "dependency_count": len(results),

        "updates_found": sum(
            item["comparison_status"] == "update_available"
            for item in results
        ),

        "lookup_failures": sum(
            item["comparison_status"] == "lookup_failed"
            for item in results
        ),

        "dependencies": results,
        "warnings": report["warnings"],
    }


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "Usage: python -m "
            "codedrift.dependency.registry_client "
            "<repository_path>"
        )

        raise SystemExit(1)

    report = check_repository_updates(sys.argv[1])

    print(json.dumps(report, indent=2))
