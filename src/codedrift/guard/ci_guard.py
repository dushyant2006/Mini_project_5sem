
import argparse
import json

from pathlib import Path

from codedrift.repository.full_analyzer import (
    analyze_full_local_repository,
    analyze_full_github_repository,
)

from codedrift.guard.upgrade_policy import (
    UpgradePolicy,
    evaluate_upgrade_policy,
)


def escape_markdown(value):

    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def generate_markdown_report(result):

    gate = result["policy_result"]

    lines = [
        "# CodeDrift CI/CD Report",
        "",
        f"**Repository:** {escape_markdown(gate['repository'])}",
        "",
        f"**Decision:** {gate['decision']}",
        "",
        "## Analysis Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        (
            "| Dependencies analyzed | "
            f"{gate['dependency_count']} |"
        ),
        (
            "| Blocking violations | "
            f"{gate['blocking_violation_count']} |"
        ),
        (
            "| Warnings | "
            f"{gate['warning_count']} |"
        ),
        "",
        "## Policy Findings",
        "",
    ]

    if not gate["violations"]:

        lines.append(
            "No configured policy violations detected."
        )

    else:

        lines.extend([
            "| Dependency | Rule | Level | Message |",
            "|---|---|---|---|",
        ])

        for violation in gate["violations"]:

            values = [
                violation.get("dependency") or "Repository",
                violation["rule"],
                violation["level"],
                violation["message"],
            ]

            escaped = [
                escape_markdown(value)
                for value in values
            ]

            lines.append(
                "| " + " | ".join(escaped) + " |"
            )

    lines.extend([
        "",
        "## Analysis Limitations",
        "",
        "This report uses static dependency analysis.",
        "",
        "The candidate is the registry's latest release,",
        "not necessarily the version proposed by a pull request.",
        "",
        "Passing this gate does not prove runtime compatibility.",
        "",
    ])

    return "\n".join(lines)


def run_ci_guard(
    target,
    policy=None,
    offline=False,
    max_comparisons=5,
):

    policy = policy or UpgradePolicy()

    if max_comparisons < 0:

        raise ValueError(
            "Maximum comparisons cannot be negative."
        )

    if str(target).startswith("https://"):

        report = analyze_full_github_repository(
            target,
            offline=offline,
            max_comparisons=max_comparisons,
        )

    else:

        report = analyze_full_local_repository(
            target,
            offline=offline,
            max_comparisons=max_comparisons,
        )

    policy_result = evaluate_upgrade_policy(
        report,
        policy,
    )

    return {
        "analysis_report": report,
        "policy_result": policy_result,
    }


def save_reports(result, output_directory):

    directory = Path(output_directory)

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = directory / "codedrift-report.json"

    markdown_path = directory / "codedrift-report.md"

    json_path.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    markdown_path.write_text(
        generate_markdown_report(result),
        encoding="utf-8",
    )

    return {
        "json_report": str(json_path),
        "markdown_report": str(markdown_path),
    }


def main():

    parser = argparse.ArgumentParser(
        description="CodeDrift CI/CD Policy Guard"
    )

    parser.add_argument(
        "target",
        help="Local repository or GitHub URL",
    )

    parser.add_argument(
        "--policy",
        default=None,
        help="Path to policy JSON file",
    )

    parser.add_argument(
        "--offline",
        action="store_true",
    )

    parser.add_argument(
        "--max-comparisons",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--output-dir",
        default="codedrift-reports",
    )

    args = parser.parse_args()

    try:

        policy = (
            UpgradePolicy.load(args.policy)
            if args.policy
            else UpgradePolicy()
        )

        result = run_ci_guard(
            args.target,
            policy=policy,
            offline=args.offline,
            max_comparisons=args.max_comparisons,
        )

        paths = save_reports(
            result,
            args.output_dir,
        )

        gate = result["policy_result"]

        print("\nCodeDrift CI/CD Policy Guard")
        print("=" * 45)

        print(
            f"Decision: {gate['decision']}"
        )

        print(
            f"Dependencies: {gate['dependency_count']}"
        )

        print(
            f"Blocking violations: "
            f"{gate['blocking_violation_count']}"
        )

        print(
            f"Warnings: {gate['warning_count']}"
        )

        print(
            f"JSON report: {paths['json_report']}"
        )

        print(
            f"Markdown report: {paths['markdown_report']}"
        )

        return gate["exit_code"]

    except Exception as error:

        print(
            f"CodeDrift analysis error: {error}"
        )

        return 2


if __name__ == "__main__":

    raise SystemExit(main())
