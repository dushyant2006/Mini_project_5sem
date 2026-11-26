
import argparse
import json
import tempfile
from pathlib import Path

from codedrift.repository.github_client import (
    clone_repository,
    validate_github_url,
    RepositoryError,
)

from codedrift.dependency.manifest_scanner import (
    analyze_repository_structure,
)

from codedrift.dependency.manifest_parser import (
    extract_dependencies,
)

from codedrift.dependency.version_resolver import (
    resolve_dependency,
)

from codedrift.dependency.registry_client import (
    check_dependency,
)

from codedrift.security.osv_client import (
    scan_dependency,
)


def analyze_local_repository(repository_path, offline=False):

    root = Path(repository_path).resolve()

    structure = analyze_repository_structure(root)
    extracted = extract_dependencies(root)

    results = []

    security_cache = {}

    for dependency in extracted["dependencies"]:

        resolved = resolve_dependency(dependency, root)

        if offline:

            results.append({
                **resolved,
                "latest_release": None,
                "comparison_status": "not_checked",
                "error": None,
                "security_status": "not_checked",
                "vulnerability_count": None,
                "vulnerabilities": [],
                "security_error": None,
            })

            continue

        lookup = dependency.copy()

        baseline = resolved["baseline_version"]

        if baseline is not None:

            if dependency["ecosystem"] == "pypi":
                lookup["constraint"] = f"=={baseline}"

            else:
                lookup["constraint"] = baseline

        checked = check_dependency(lookup)

        cache_key = (
            resolved["ecosystem"],
            resolved["name"],
            baseline,
        )

        if cache_key not in security_cache:

            security = scan_dependency(resolved)

            security_cache[cache_key] = {
                "security_status": security["security_status"],
                "vulnerability_count": security["vulnerability_count"],
                "vulnerabilities": security["vulnerabilities"],
                "security_error": security["security_error"],
            }

        results.append({
            **resolved,
            "latest_release": checked["latest_release"],
            "comparison_status": checked["comparison_status"],
            "error": checked["error"],
            **security_cache[cache_key],
        })

    unique_cve_ids = sorted({
        cve_id
        for item in results
        for vulnerability in item["vulnerabilities"]
        for cve_id in vulnerability.get("cve_ids", [])
    })

    unique_advisory_ids = sorted({
        vulnerability["id"]
        for item in results
        for vulnerability in item["vulnerabilities"]
    })

    return {
        "repository": root.name,
        "languages": structure["languages"],
        "ecosystems": structure["ecosystems"],
        "manifests": structure["manifests"],

        "dependency_count": len(results),

        "updates_found": sum(
            item["comparison_status"] == "update_available"
            for item in results
        ),

        "unresolved_versions": sum(
            item["baseline_version"] is None
            for item in results
        ),

        "lookup_failures": sum(
            item["comparison_status"] == "lookup_failed"
            for item in results
        ),

        "vulnerable_dependencies": sum(
            item["security_status"] == "vulnerable"
            for item in results
        ),

        "vulnerabilities_found": sum(
            item["vulnerability_count"] or 0
            for item in results
        ),

        "unique_advisory_count": len(unique_advisory_ids),

        "unique_advisory_ids": unique_advisory_ids,

        "unique_cve_count": len(unique_cve_ids),

        "unique_cve_ids": unique_cve_ids,

        "security_checked": sum(
            item["security_status"] in {
                "vulnerable",
                "no_known_vulnerabilities",
            }
            for item in results
        ),

        "security_lookup_failures": sum(
            item["security_status"] == "lookup_failed"
            for item in results
        ),

        "security_unchecked": sum(
            item["security_status"] in {
                "not_checked",
                "unresolved_version",
                "unsupported_ecosystem",
            }
            for item in results
        ),

        "dependencies": results,
        "warnings": extracted["warnings"],
        "offline": offline,
    }


def analyze_github_repository(repository_url, offline=False):

    safe_url = validate_github_url(repository_url)

    repository_name = (
        safe_url.rsplit("/", 1)[-1]
        .removesuffix(".git")
    )

    with tempfile.TemporaryDirectory(
        prefix="codedrift_",
        ignore_cleanup_errors=True,
    ) as workspace:

        destination = Path(workspace) / repository_name

        clone_repository(safe_url, destination)

        report = analyze_local_repository(
            destination,
            offline=offline,
        )

        report["repository_url"] = safe_url

        return report


def main():

    parser = argparse.ArgumentParser(
        description="CodeDrift repository analyzer"
    )

    parser.add_argument(
        "target",
        help="GitHub repository URL or local directory",
    )

    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip package registry and OSV requests",
    )

    args = parser.parse_args()

    try:

        if args.target.startswith("https://"):

            report = analyze_github_repository(
                args.target,
                offline=args.offline,
            )

        else:

            report = analyze_local_repository(
                args.target,
                offline=args.offline,
            )

        print(json.dumps(report, indent=2))

    except (RepositoryError, ValueError, OSError) as error:

        parser.exit(
            status=1,
            message=f"CodeDrift error: {error}\n",
        )


if __name__ == "__main__":
    main()
