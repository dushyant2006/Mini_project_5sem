"""
Unit Tests for Codemod Patch Generator and Migration Guide.
"""
from pathlib import Path
from codedrift.core.models import BlastRadiusReport, BlastRadiusItem, APIChange, CallSite
from codedrift.remediation.patch_generator import PatchGenerator
from codedrift.remediation.migration_guide import MigrationGuideSynthesizer


def test_remediation_generates_diff_for_removed_parameter(tmp_path: Path):
    target_file = tmp_path / "checkout.py"
    target_file.write_text("process_payment(amount=100, currency='USD')\n", encoding="utf-8")

    change = APIChange(
        change_type="PARAMETER_REMOVED",
        qualified_name="payment.process_payment",
        parameter_name="currency",
        is_breaking=True,
    )
    call_site = CallSite(
        file_path=str(target_file),
        line=1,
        column=0,
        caller_function=None,
        callee_name="process_payment",
        matched_target="payment.process_payment",
        code_snippet="process_payment(amount=100, currency='USD')",
        arguments_passed=["amount=100", "currency='USD'"],
    )

    item = BlastRadiusItem(change=change, call_sites=[call_site], is_reachable=True, impact_score=1.0)
    report = BlastRadiusReport(
        client_dir=str(tmp_path),
        total_breaking_upstream=1,
        reachable_breaking_count=1,
        blast_radius_score=25.0,
        items=[item],
        affected_files=[str(target_file)],
    )

    patcher = PatchGenerator()
    patches = patcher.generate_patches(report)

    assert len(patches) == 1
    patch = patches[0]
    assert "currency" not in patch.patched_code
    assert "amount=100" in patch.patched_code

    guide_synth = MigrationGuideSynthesizer()
    guide = guide_synth.generate_markdown(report)
    assert "CodeDrift Autonomous Migration Guide" in guide
    assert "PARAMETER_REMOVED" in guide
