
import argparse
import json

from urllib.request import Request, urlopen
from urllib.error import URLError
from packaging.utils import canonicalize_name


OSV_API_URL = "https://api.osv.dev/v1/query"

REQUEST_TIMEOUT = 15

MAX_RESPONSE_BYTES = 10_000_000

ECOSYSTEM_MAPPING = {
    "pypi": "PyPI",
    "npm": "npm",
    "maven": "Maven",
}


class OSVError(Exception):
    pass


def fetch_vulnerabilities(name, version, ecosystem):

    osv_ecosystem = ECOSYSTEM_MAPPING.get(ecosystem)

    if osv_ecosystem is None:
        raise OSVError("Unsupported ecosystem")

    if ecosystem == "pypi":
        name = canonicalize_name(name)

    payload = {
        "version": version,
        "package": {
            "name": name,
            "ecosystem": osv_ecosystem,
        },
    }

    vulnerabilities = []
    seen_tokens = set()

    try:

        for _ in range(20):

            request = Request(
                OSV_API_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "CodeDrift/2.0",
                },
                method="POST",
            )

            with urlopen(
                request,
                timeout=REQUEST_TIMEOUT,
            ) as response:

                raw = response.read(
                    MAX_RESPONSE_BYTES + 1
                )

            if len(raw) > MAX_RESPONSE_BYTES:
                raise OSVError("OSV response too large")

            data = json.loads(raw)

            if not isinstance(data, dict):
                raise OSVError("Invalid OSV response")

            if "error" in data:
                raise OSVError(str(data["error"]))

            records = data.get("vulns", [])

            if not isinstance(records, list):
                raise OSVError("Invalid vulnerability records")

            if any(
                not isinstance(item, dict)
                or not item.get("id")
                for item in records
            ):
                raise OSVError("Malformed vulnerability record")

            vulnerabilities.extend(records)

            token = data.get("next_page_token")

            if not token:
                return vulnerabilities

            if not isinstance(token, str) or token in seen_tokens:
                raise OSVError("Invalid pagination token")

            seen_tokens.add(token)

            payload["page_token"] = token

        raise OSVError("OSV pagination limit exceeded")

    except (
        URLError,
        OSError,
        ValueError,
    ) as error:

        raise OSVError(
            f"OSV request failed: {error}"
        ) from error


def normalize_vulnerability(vulnerability, name, ecosystem):

    fixed_versions = set()

    osv_ecosystem = ECOSYSTEM_MAPPING.get(ecosystem)

    for affected in vulnerability.get("affected", []):

        package = affected.get("package", {})

        affected_name = package.get("name", "")

        if ecosystem == "pypi":

            matches = (
                canonicalize_name(affected_name)
                == canonicalize_name(name)
            )

        else:

            matches = affected_name == name

        if not matches:
            continue

        if package.get("ecosystem") != osv_ecosystem:
            continue

        for version_range in affected.get("ranges", []):

            if version_range.get("type") == "GIT":
                continue

            for event in version_range.get("events", []):

                if "fixed" in event:

                    fixed_versions.add(event["fixed"])

    aliases = vulnerability.get("aliases", [])

    return {
        "id": vulnerability.get("id"),
        "summary": vulnerability.get("summary", ""),
        "details": vulnerability.get("details", ""),
        "aliases": aliases,

        "cve_ids": [
            alias for alias in aliases
            if alias.startswith("CVE-")
        ],

        "severity": vulnerability.get("severity", []),

        "fixed_versions": sorted(fixed_versions),

        "published": vulnerability.get("published"),

        "modified": vulnerability.get("modified"),

        "references": [
            reference["url"]
            for reference in vulnerability.get("references", [])
            if "url" in reference
        ],
    }


def scan_dependency(dependency):

    name = dependency["name"]

    ecosystem = dependency["ecosystem"]

    version = dependency.get("baseline_version")

    result = {
        **dependency,
        "vulnerability_count": None,
        "vulnerabilities": [],
        "security_status": "not_checked",
        "security_error": None,
    }

    if version is None:

        result["security_status"] = "unresolved_version"

        return result

    if ecosystem not in ECOSYSTEM_MAPPING:

        result["security_status"] = "unsupported_ecosystem"

        return result

    try:

        records = fetch_vulnerabilities(
            name,
            version,
            ecosystem,
        )

        vulnerabilities = {}

        for record in records:

            if record.get("withdrawn"):
                continue

            normalized = normalize_vulnerability(
                record,
                name,
                ecosystem,
            )

            vulnerabilities[normalized["id"]] = normalized

        result["vulnerabilities"] = list(
            vulnerabilities.values()
        )

        result["vulnerability_count"] = len(
            vulnerabilities
        )

        if vulnerabilities:

            result["security_status"] = "vulnerable"

        else:

            result["security_status"] = "no_known_vulnerabilities"

    except OSVError as error:

        result["security_status"] = "lookup_failed"

        result["security_error"] = str(error)

    return result


def main():

    parser = argparse.ArgumentParser(
        description="CodeDrift vulnerability scanner"
    )

    parser.add_argument("name")

    parser.add_argument("version")

    parser.add_argument(
        "ecosystem",
        choices=["pypi", "npm", "maven"],
    )

    args = parser.parse_args()

    dependency = {
        "name": args.name,
        "ecosystem": args.ecosystem,
        "baseline_version": args.version,
    }

    result = scan_dependency(dependency)

    print(json.dumps(result, indent=2))

    if result["security_status"] == "lookup_failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
