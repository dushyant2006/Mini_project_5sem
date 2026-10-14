"""
Autonomous Developer Migration Guide Synthesizer.
Produces clear, human-readable step-by-step migration manuals
for upgrading breaking dependency versions.
"""
from typing import List
from ..core.models import BlastRadiusReport


class MigrationGuideSynthesizer:
    """
    Synthesizes developer migration instructions from blast radius analysis.
    """

    def generate_markdown(self, report: BlastRadiusReport) -> str:
        md = []
        md.append("# CodeDrift Autonomous Migration Guide")
        md.append(f"**Target Client Directory:** `{report.client_dir}`")
        md.append(f"**Blast Radius Risk Score:** `{report.blast_radius_score} / 100`")
        md.append(f"**Reachable Breaking Changes:** `{report.reachable_breaking_count}` of `{report.total_breaking_upstream}`\n")

        if report.reachable_breaking_count == 0:
            md.append("> [!NOTE]")
            md.append("> **Safe to Auto-Merge!** All upstream breaking changes reside in unused code paths.\n")
            return "\n".join(md)

        md.append("## Required Remediation Actions\n")

        for idx, item in enumerate(report.items, 1):
            if not item.is_reachable:
                continue

            change = item.change
            md.append(f"### {idx}. {change.change_type}: `{change.qualified_name}`")
            md.append(f"- **Severity:** `{change.severity}`")
            md.append(f"- **Description:** {change.description}")
            if change.suggested_migration:
                md.append(f"- **Recommendation:** {change.suggested_migration}")

            md.append("\n**Affected Call Sites in Your Code:**")
            for cs in item.call_sites:
                md.append(f"- `{cs.file_path}:{cs.line}` inside function `{cs.caller_function or '<module>'}`")
                md.append(f"  ```python\n  {cs.code_snippet}\n  ```")
            md.append("")

        md.append("---")
        md.append("*Generated automatically by CodeDrift Autonomous Dependency Guard.*")
        return "\n".join(md)
