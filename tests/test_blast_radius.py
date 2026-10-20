"""
Unit Tests for Reachability Filtering and Blast Radius Risk Scoring.
"""
import tempfile
from pathlib import Path
from codedrift.impact.blast_radius import BlastRadiusAnalyzer
from codedrift.core.models import DiffResult, APIChange


def test_blast_radius_filters_unreachable_breaking_changes(tmp_path: Path = None):
    if tmp_path is None:
        with tempfile.TemporaryDirectory() as td:
            _run_blast_test(Path(td))
    else:
        _run_blast_test(tmp_path)


def _run_blast_test(tmp_path: Path):
    # Client only calls process_payment, does NOT call delete_all_records
    client_code = """
from paymentlib import process_payment

def run():
    process_payment(amount=50)
"""
    client_file = tmp_path / "app.py"
    client_file.write_text(client_code, encoding="utf-8")

    diff = DiffResult(
        changes=[
            APIChange(
                change_type="FUNCTION_REMOVED",
                qualified_name="paymentlib.process_payment",
                is_breaking=True,
                severity="HIGH",
            ),
            APIChange(
                change_type="FUNCTION_REMOVED",
                qualified_name="paymentlib.delete_all_records",
                is_breaking=True,
                severity="CRITICAL",
            ),
        ]
    )

    analyzer = BlastRadiusAnalyzer()
    report = analyzer.analyze(diff, client_dir=tmp_path)

    assert report.total_breaking_upstream == 2
    # Only 1 is reachable!
    assert report.reachable_breaking_count == 1
    assert report.blast_radius_score > 0.0

    reachable_items = [it for it in report.items if it.is_reachable]
    assert len(reachable_items) == 1
    assert reachable_items[0].change.qualified_name == "paymentlib.process_payment"
