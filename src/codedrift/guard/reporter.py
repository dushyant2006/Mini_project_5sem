"""
Multi-Target Reporting Subsystem for CodeDrift.
Renders beautiful Rich terminal dashboards, GitHub Actions markdown summaries,
and machine-readable JSON/SARIF.
"""
import json
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..core.enums import GateDecision, Severity
from ..core.models import BlastRadiusReport, DiffResult, PolicyResult


class DriftReporter:
    """
    Renders CodeDrift findings across multiple output formats.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def print_diff_table(self, diff_result: DiffResult) -> None:
        table = Table(
            title="[bold cyan]CodeDrift API Contract Differential[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Severity", style="bold", width=10)
        table.add_column("Type", width=26)
        table.add_column("Symbol / Function", width=35)
        table.add_column("Breaking?", justify="center", width=10)
        table.add_column("Description", width=40)

        for change in diff_result.changes:
            sev_color = {
                "CRITICAL": "red",
                "HIGH": "bright_red",
                "MEDIUM": "yellow",
                "LOW": "green",
                "INFO": "blue",
            }.get(change.severity, "white")

            breaking_str = "[bold red]YES[/bold red]" if change.is_breaking else "[green]NO[/green]"

            table.add_row(
                f"[{sev_color}]{change.severity}[/{sev_color}]",
                change.change_type,
                change.qualified_name,
                breaking_str,
                change.description,
            )

        self.console.print(table)

    def print_blast_radius_summary(self, report: BlastRadiusReport) -> None:
        risk_color = "red" if report.blast_radius_score > 30 else ("yellow" if report.blast_radius_score > 0 else "green")

        summary_text = Text()
        summary_text.append(f"Client Directory: ", style="bold")
        summary_text.append(f"{report.client_dir}\n")
        summary_text.append(f"Upstream Breaking Changes: ", style="bold")
        summary_text.append(f"{report.total_breaking_upstream}\n")
        summary_text.append(f"Reachable in Client Code: ", style="bold")
        summary_text.append(f"{report.reachable_breaking_count}\n", style="bold red" if report.reachable_breaking_count > 0 else "bold green")
        summary_text.append(f"Blast Radius Impact Score: ", style="bold")
        summary_text.append(f"{report.blast_radius_score} / 100\n", style=f"bold {risk_color}")
        summary_text.append(f"Affected Source Files: ", style="bold")
        summary_text.append(f"{len(report.affected_files)}")

        self.console.print(
            Panel(
                summary_text,
                title="[bold yellow]CodeDrift Blast Radius Assessment[/bold yellow]",
                border_style=risk_color,
            )
        )

    def print_gate_decision(self, policy_result: PolicyResult) -> None:
        if policy_result.decision == GateDecision.PASSED:
            self.console.print(
                Panel(
                    f"[bold green]{policy_result.summary}[/bold green]",
                    title="CI/CD Quality Gate: PASSED",
                    border_style="green",
                )
            )
        else:
            violation_details = "\n".join(f"• {v}" for v in policy_result.violations)
            self.console.print(
                Panel(
                    f"[bold red]{policy_result.summary}[/bold red]\n\n{violation_details}",
                    title="CI/CD Quality Gate: BLOCKED",
                    border_style="red",
                )
            )

    def to_json(
        self,
        diff_result: DiffResult,
        blast_report: Optional[BlastRadiusReport] = None,
        policy_result: Optional[PolicyResult] = None,
    ) -> str:
        data = {
            "diff": diff_result.to_dict(),
            "blast_radius": blast_report.to_dict() if blast_report else None,
            "policy": policy_result.to_dict() if policy_result else None,
        }
        return json.dumps(data, indent=2)

    def to_markdown(
        self,
        diff_result: DiffResult,
        blast_report: Optional[BlastRadiusReport] = None,
        policy_result: Optional[PolicyResult] = None,
    ) -> str:
        md = []
        md.append("## 🛡️ CodeDrift Dependency Guard Report\n")
        
        if policy_result:
            status_badge = "✅ **PASSED**" if policy_result.decision == GateDecision.PASSED else "❌ **BLOCKED**"
            md.append(f"**Gate Decision:** {status_badge}")
            md.append(f"**Summary:** {policy_result.summary}\n")

        if blast_report:
            md.append(f"- **Blast Radius Score:** `{blast_report.blast_radius_score}/100`")
            md.append(f"- **Reachable Breaking Changes:** `{blast_report.reachable_breaking_count}` of `{blast_report.total_breaking_upstream}`")
            md.append(f"- **Affected Files:** {len(blast_report.affected_files)}\n")

        md.append("### Detected API Changes")
        md.append("| Severity | Type | Target | Breaking |")
        md.append("| :--- | :--- | :--- | :--- |")
        for c in diff_result.changes:
            brk = "🚨 YES" if c.is_breaking else "🟢 NO"
            md.append(f"| {c.severity} | {c.change_type} | `{c.qualified_name}` | {brk} |")

        return "\n".join(md)
