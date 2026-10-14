"""
Unit Tests for CodeDrift Semantic Diff & Breaking Change Detection Engine.
"""
from codedrift.parser import PythonParser
from codedrift.detection import DiffEngine
from codedrift.core.enums import Severity, ChangeType


def test_diff_function_removal():
    old_code = "def process_payment(amount: float): pass"
    new_code = "def other_function(): pass"

    parser = PythonParser()
    old_mod = parser.parse_code(old_code, module_name="payment")
    new_mod = parser.parse_code(new_code, module_name="payment")

    diff = DiffEngine().compare(old_mod, new_mod)

    assert len(diff.breaking_changes) == 1
    change = diff.breaking_changes[0]
    assert change.change_type == ChangeType.FUNCTION_REMOVED.value
    assert change.severity == Severity.CRITICAL.value
    assert change.is_breaking is True


def test_diff_mandatory_vs_optional_parameter():
    old_code = "def send_email(to: str): pass"
    new_code = "def send_email(to: str, subject: str, cc: str = None): pass"

    parser = PythonParser()
    old_mod = parser.parse_code(old_code, module_name="mailer")
    new_mod = parser.parse_code(new_code, module_name="mailer")

    diff = DiffEngine().compare(old_mod, new_mod)

    # 'subject' is mandatory (breaking), 'cc' is optional (non-breaking)
    breaking = [c for c in diff.changes if c.parameter_name == "subject"]
    optional = [c for c in diff.changes if c.parameter_name == "cc"]

    assert len(breaking) == 1
    assert breaking[0].change_type == ChangeType.PARAMETER_ADDED_MANDATORY.value
    assert breaking[0].is_breaking is True

    assert len(optional) == 1
    assert optional[0].change_type == ChangeType.PARAMETER_ADDED_OPTIONAL.value
    assert optional[0].is_breaking is False


def test_diff_return_type_mutation():
    old_code = "def query() -> list: pass"
    new_code = "def query() -> dict: pass"

    parser = PythonParser()
    old_mod = parser.parse_code(old_code, module_name="api")
    new_mod = parser.parse_code(new_code, module_name="api")

    diff = DiffEngine().compare(old_mod, new_mod)
    assert any(c.change_type == ChangeType.RETURN_TYPE_CHANGED.value for c in diff.changes)
