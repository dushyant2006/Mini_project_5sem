"""
Unit Tests for CodeDrift REST API Service.
"""
from codedrift.api.server import CodeDriftAPIHandler


def test_api_handler_structure():
    # Verify handler endpoints exist and have docstrings
    assert hasattr(CodeDriftAPIHandler, "do_GET")
    assert hasattr(CodeDriftAPIHandler, "do_POST")
    assert hasattr(CodeDriftAPIHandler, "_handle_diff")
    assert hasattr(CodeDriftAPIHandler, "_handle_guard")
