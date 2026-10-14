"""
Unit Tests for Static CallGraph Builder and Symbol Resolution.
"""
from pathlib import Path
from codedrift.impact.callgraph import CallGraphBuilder


def test_callgraph_extracts_invocations_and_aliases(tmp_path: Path):
    client_code = """
import paymentlib as p
from authlib import authenticate

def checkout():
    user = authenticate(token="xyz")
    res = p.charge(amount=100)
"""
    client_file = tmp_path / "service.py"
    client_file.write_text(client_code, encoding="utf-8")

    builder = CallGraphBuilder()
    sites = builder.scan_file(client_file)

    assert len(sites) >= 2
    callees = {s.callee_name for s in sites}
    assert "authenticate" in callees
    assert "p.charge" in callees

    charge_site = next(s for s in sites if s.callee_name == "p.charge")
    assert charge_site.matched_target == "paymentlib.charge"
    assert charge_site.caller_function == "checkout"
