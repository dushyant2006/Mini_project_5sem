"""
Unified Command-Line Interface (CLI) for CodeDrift.
Provides commands for API diffing, blast-radius calculation, CI quality gates, and remediation.
"""
import argparse
import sys
from pathlib import Path
from typing import List, Optional

from rich.console import Console

from .core.config import GuardPolicy
from .core.enums import GateDecision
from .detection.diff_engine import DiffEngine
from .detection.semver_checker import SemVerAuditor
from .guard.policy_engine import PolicyEngine
from .guard.reporter import DriftReporter
from .impact.blast_radius import BlastRadiusAnalyzer
from .parser.python_parser import PythonParser
from .remediation.migration_guide import MigrationGuideSynthesizer
from .remediation.patch_generator import PatchGenerator


console = Console()


def diff_command(args: argparse.Namespace) -> int:
    parser = PythonParser()
    old_info = parser.parse_file(args.old_file)
    new_info = parser.parse_file(args.new_file)

    engine = DiffEngine()
    diff_result = engine.compare(old_info, new_info)

    reporter = DriftReporter(console)
    if args.json:
        console.print(reporter.to_json(diff_result))
    else:
        reporter.print_diff_table(diff_result)

    return 0


def audit_command(args: argparse.Namespace) -> int:
    parser = PythonParser()
    old_info = parser.parse_file(args.old_file)
    new_info = parser.parse_file(args.new_file)

    engine = DiffEngine()
    diff_result = engine.compare(old_info, new_info)

    auditor = SemVerAuditor()
    audit_res = auditor.audit_bump(args.old_version, args.new_version, diff_result)

    console.print(f"[bold cyan]CodeDrift SemVer Compliance Audit:[/bold cyan]")
    console.print(f"Bump: [yellow]{args.old_version}[/yellow] -> [yellow]{args.new_version}[/yellow] ({audit_res['bump_type']})")
    
    if audit_res["valid"]:
        console.print("[bold green][PASS] Version bump satisfies SemVer specification.[/bold green]")
        return 0
    else:
        console.print("[bold red][FAIL] SemVer Violation Detected![/bold red]")
        for v in audit_res["violations"]:
            console.print(f"  * [red]{v}[/red]")
        return 1


def blast_radius_command(args: argparse.Namespace) -> int:
    parser = PythonParser()
    old_info = parser.parse_file(args.old_file)
    new_info = parser.parse_file(args.new_file)

    engine = DiffEngine()
    diff_result = engine.compare(old_info, new_info)

    analyzer = BlastRadiusAnalyzer()
    report = analyzer.analyze(diff_result, client_dir=args.client, target_package_name=args.package)

    reporter = DriftReporter(console)
    if args.json:
        console.print(reporter.to_json(diff_result, blast_report=report))
    else:
        reporter.print_diff_table(diff_result)
        reporter.print_blast_radius_summary(report)

    return 0


def guard_command(args: argparse.Namespace) -> int:
    parser = PythonParser()
    old_info = parser.parse_file(args.old_file)
    new_info = parser.parse_file(args.new_file)

    engine = DiffEngine()
    diff_result = engine.compare(old_info, new_info)

    report = None
    if args.client:
        analyzer = BlastRadiusAnalyzer()
        report = analyzer.analyze(diff_result, client_dir=args.client, target_package_name=args.package)

    policy = GuardPolicy(max_allowable_blast_radius=args.max_score)
    policy_engine = PolicyEngine(policy)
    policy_result = policy_engine.evaluate(diff_result, blast_report=report)

    reporter = DriftReporter(console)
    if args.json:
        console.print(reporter.to_json(diff_result, blast_report=report, policy_result=policy_result))
    else:
        reporter.print_diff_table(diff_result)
        if report:
            reporter.print_blast_radius_summary(report)
        reporter.print_gate_decision(policy_result)

    return policy_result.exit_code


def remediate_command(args: argparse.Namespace) -> int:
    parser = PythonParser()
    old_info = parser.parse_file(args.old_file)
    new_info = parser.parse_file(args.new_file)

    engine = DiffEngine()
    diff_result = engine.compare(old_info, new_info)

    analyzer = BlastRadiusAnalyzer()
    report = analyzer.analyze(diff_result, client_dir=args.client, target_package_name=args.package)

    guide_synth = MigrationGuideSynthesizer()
    guide = guide_synth.generate_markdown(report)

    patcher = PatchGenerator()
    patches = patcher.generate_patches(report)

    console.print(guide)

    if patches:
        console.print("\n[bold green]Synthesized Automated Codemod Patches:[/bold green]")
        for p in patches:
            console.print(f"[bold cyan]File: {p.file_path}[/bold cyan]")
            console.print(p.diff)
    else:
        console.print("\n[italic yellow]No automated syntactic line rewrites needed.[/italic yellow]")

    return 0


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="codedrift",
        description="CodeDrift: Autonomous API Breaking-Change & Dependency Degradation Guard",
    )
    sub = root.add_subparsers(dest="command", required=True)

    # diff
    p_diff = sub.add_parser("diff", help="Calculate semantic API diff between two files")
    p_diff.add_argument("old_file", help="Path to base library file")
    p_diff.add_argument("new_file", help="Path to new library file")
    p_diff.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_diff.set_defaults(func=diff_command)

    # audit
    p_audit = sub.add_parser("audit", help="Audit SemVer compliance for a version bump")
    p_audit.add_argument("old_version", help="Previous version (e.g. 1.2.0)")
    p_audit.add_argument("new_version", help="Proposed version (e.g. 1.3.0)")
    p_audit.add_argument("old_file", help="Path to base library file")
    p_audit.add_argument("new_file", help="Path to new library file")
    p_audit.set_defaults(func=audit_command)

    # blast-radius
    p_blast = sub.add_parser("blast-radius", help="Calculate downstream reachability and blast radius")
    p_blast.add_argument("old_file", help="Path to base library file")
    p_blast.add_argument("new_file", help="Path to new library file")
    p_blast.add_argument("--client", required=True, help="Path to client directory to analyze")
    p_blast.add_argument("--package", help="Optional library package name to filter symbols")
    p_blast.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_blast.set_defaults(func=blast_radius_command)

    # guard
    p_guard = sub.add_parser("guard", help="Run CI/CD quality gate check with exit code")
    p_guard.add_argument("old_file", help="Path to base library file")
    p_guard.add_argument("new_file", help="Path to new library file")
    p_guard.add_argument("--client", help="Path to client directory to analyze")
    p_guard.add_argument("--package", help="Optional library package name")
    p_guard.add_argument("--max-score", type=float, default=0.0, help="Max allowable blast score (default 0.0)")
    p_guard.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_guard.set_defaults(func=guard_command)

    # remediate
    p_remed = sub.add_parser("remediate", help="Generate automated patch and migration guide")
    p_remed.add_argument("old_file", help="Path to base library file")
    p_remed.add_argument("new_file", help="Path to new library file")
    p_remed.add_argument("--client", required=True, help="Path to client directory to analyze")
    p_remed.add_argument("--package", help="Optional library package name")
    p_remed.set_defaults(func=remediate_command)

    # report
    p_rep = sub.add_parser("report", help="Generate standalone interactive HTML report")
    p_rep.add_argument("old_file", help="Path to base library file")
    p_rep.add_argument("new_file", help="Path to new library file")
    p_rep.add_argument("--client", help="Path to client directory to analyze")
    p_rep.add_argument("--package", help="Optional library package name")
    p_rep.add_argument("--max-score", type=float, default=0.0, help="Max allowable blast score (default 0.0)")
    p_rep.add_argument("-o", "--output", default="codedrift_report.html", help="Output HTML file path (default: codedrift_report.html)")
    p_rep.set_defaults(func=report_command)

    # ui
    p_ui = sub.add_parser("ui", help="Launch interactive Streamlit Web Dashboard")
    p_ui.set_defaults(func=ui_command)

    return root


def report_command(args: argparse.Namespace) -> int:
    parser = PythonParser()
    old_info = parser.parse_file(args.old_file)
    new_info = parser.parse_file(args.new_file)

    engine = DiffEngine()
    diff_result = engine.compare(old_info, new_info)

    report = None
    if args.client:
        analyzer = BlastRadiusAnalyzer()
        report = analyzer.analyze(diff_result, client_dir=args.client, target_package_name=args.package)

    policy = GuardPolicy(max_allowable_blast_radius=args.max_score)
    policy_engine = PolicyEngine(policy)
    policy_result = policy_engine.evaluate(diff_result, blast_report=report)

    reporter = DriftReporter(console)
    html_content = reporter.to_html(diff_result, blast_report=report, policy_result=policy_result)

    output_path = Path(args.output)
    output_path.write_text(html_content, encoding="utf-8")
    console.print(f"[bold green][OK] Standalone Interactive HTML Report generated at: [cyan]{output_path.resolve()}[/cyan][/bold green]")
    return 0


def ui_command(args: argparse.Namespace) -> int:
    import subprocess
    dashboard_path = Path(__file__).parent / "dashboard.py"
    console.print("[bold green]Starting CodeDrift Interactive Web Dashboard on Streamlit...[/bold green]")
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(dashboard_path)])


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
