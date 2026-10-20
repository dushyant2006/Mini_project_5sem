"""
Unit Tests for CodeDrift CLI Parser and Subcommands.
"""
from codedrift.cli import build_parser, main


def test_cli_parser_build():
    parser = build_parser()
    # Test valid subcommands parse cleanly
    args_diff = parser.parse_args(["diff", "file1.py", "file2.py"])
    assert args_diff.command == "diff"
    assert args_diff.old_file == "file1.py"

    args_audit = parser.parse_args(["audit", "1.0.0", "2.0.0", "f1.py", "f2.py"])
    assert args_audit.command == "audit"
    assert args_audit.old_version == "1.0.0"

    args_guard = parser.parse_args(["guard", "f1.py", "f2.py", "--client", "app/"])
    assert args_guard.command == "guard"
    assert args_guard.client == "app/"

    args_predict = parser.parse_args(["predict", "f1.py", "f2.py", "--client", "app/"])
    assert args_predict.command == "predict"


def test_cli_diff_execution():
    exit_code = main(["diff", "data/fixtures/v1/payment_gateway.py", "data/fixtures/v2/payment_gateway.py"])
    assert exit_code == 0
