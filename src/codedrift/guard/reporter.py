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
            violation_details = "\n".join(f"* {v}" for v in policy_result.violations)
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

    def to_html(
        self,
        diff_result: DiffResult,
        blast_report: Optional[BlastRadiusReport] = None,
        policy_result: Optional[PolicyResult] = None,
    ) -> str:
        gate_status = policy_result.decision.value if policy_result else "UNKNOWN"
        is_passed = gate_status == "PASSED"
        gate_color = "#10b981" if is_passed else "#ef4444"
        gate_badge = f'<span style="background:{gate_color};color:white;padding:4px 12px;border-radius:12px;font-weight:bold;">{gate_status}</span>'

        rows = ""
        for c in diff_result.changes:
            sev_color = {
                "CRITICAL": "#ef4444",
                "HIGH": "#f97316",
                "MEDIUM": "#eab308",
                "LOW": "#10b981",
            }.get(c.severity, "#6b7280")
            breaking_badge = '<span style="color:#ef4444;font-weight:bold;">YES</span>' if c.is_breaking else '<span style="color:#10b981;">NO</span>'
            rows += f"""<tr>
                <td><span style="color:{sev_color};font-weight:bold;">{c.severity}</span></td>
                <td><code>{c.change_type}</code></td>
                <td><code>{c.qualified_name}</code></td>
                <td style="text-align:center;">{breaking_badge}</td>
                <td>{c.description}</td>
            </tr>"""

        callsite_blocks = ""
        if blast_report:
            for item in blast_report.items:
                if item.is_reachable:
                    sites_html = "".join(f"<li><code>{cs.file_path}:{cs.line}</code> inside <code>{cs.caller_function or '<module>'}</code><pre style='background:#1f2937;color:#f3f4f6;padding:8px;border-radius:6px;margin:4px 0;'>{cs.code_snippet}</pre></li>" for cs in item.call_sites)
                    callsite_blocks += f"""<div style="background:#fff;border:1px solid #e5e7eb;border-left:4px solid #ef4444;border-radius:8px;padding:16px;margin-bottom:12px;">
                        <h4 style="margin:0 0 8px 0;color:#111827;">🚨 REACHABLE: <code>{item.change.qualified_name}</code> ({item.change.change_type})</h4>
                        <p style="margin:4px 0;color:#4b5563;">{item.change.description}</p>
                        <p style="margin:4px 0;color:#2563eb;"><strong>Recommendation:</strong> {item.change.suggested_migration or 'Update call sites.'}</p>
                        <ul style="margin:8px 0 0 20px;">{sites_html}</ul>
                    </div>"""
                else:
                    callsite_blocks += f"""<div style="background:#f9fafb;border:1px solid #e5e7eb;border-left:4px solid #10b981;border-radius:8px;padding:12px;margin-bottom:8px;">
                        <span style="color:#10b981;font-weight:bold;">🟢 UNREACHABLE (Dead Upstream Code):</span> <code>{item.change.qualified_name}</code>
                    </div>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CodeDrift Guard Dashboard</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f3f4f6; color: #1f2937; margin: 0; padding: 24px; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
.header {{ display: flex; justify-content: space-between; align-items: center; background: white; padding: 24px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 24px; }}
.metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }}
.card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
.card-title {{ font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; margin-bottom: 8px; }}
.card-val {{ font-size: 28px; font-weight: 800; color: #111827; }}
table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 24px; }}
th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
th {{ background: #f9fafb; font-size: 13px; text-transform: uppercase; color: #4b5563; font-weight: 700; }}
code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: #e5e7eb; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <h1 style="margin:0;font-size:24px;color:#111827;">🛡️ CodeDrift Dependency Guard Report</h1>
            <p style="margin:4px 0 0 0;color:#6b7280;">Continuous API Contract & Call-Graph Reachability Assessment</p>
        </div>
        <div>
            {gate_badge}
        </div>
    </div>

    <div class="metrics">
        <div class="card">
            <div class="card-title">Total Changes</div>
            <div class="card-val">{len(diff_result.changes)}</div>
        </div>
        <div class="card">
            <div class="card-title">Breaking Changes</div>
            <div class="card-val" style="color:#ef4444;">{len(diff_result.breaking_changes)}</div>
        </div>
        <div class="card">
            <div class="card-title">Reachable in Client</div>
            <div class="card-val" style="color:{'#ef4444' if (blast_report and blast_report.reachable_breaking_count > 0) else '#10b981'};">{blast_report.reachable_breaking_count if blast_report else 'N/A'}</div>
        </div>
        <div class="card">
            <div class="card-title">Blast Radius Score</div>
            <div class="card-val" style="color:{'#ef4444' if (blast_report and blast_report.blast_radius_score > 30) else '#10b981'};">{blast_report.blast_radius_score if blast_report else '0.0'} / 100</div>
        </div>
    </div>

    <h2 style="font-size:18px;margin-bottom:12px;">🧭 Call Graph & Reachability Impact</h2>
    {callsite_blocks}

    <h2 style="font-size:18px;margin:24px 0 12px 0;">📋 Semantic API Changes Differential</h2>
    <table>
        <thead>
            <tr><th>Severity</th><th>Type</th><th>Symbol</th><th>Breaking</th><th>Description</th></tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</div>
</body>
</html>"""
