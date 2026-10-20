try:
    import pytest
except ImportError:
    pytest = None

from codedrift.parser import PythonParser
from codedrift.core.exceptions import ParsingError


def test_parse_simple_function():
    code = """
def calculate_tax(amount: float, rate: float = 0.05) -> float:
    '''Calculates sale tax.'''
    if amount < 0:
        raise ValueError("Invalid amount")
    return amount * rate
"""
    parser = PythonParser()
    module = parser.parse_code(code, module_name="tax_service")

    assert module.module_name == "tax_service"
    assert len(module.functions) == 1
    fn = module.functions[0]
    assert fn.name == "calculate_tax"
    assert fn.qualified_name == "tax_service.calculate_tax"
    assert fn.return_type == "float"
    assert len(fn.parameters) == 2
    assert fn.parameters[0].name == "amount"
    assert fn.parameters[0].annotation == "float"
    assert fn.parameters[0].default is None
    assert fn.parameters[1].name == "rate"
    assert fn.parameters[1].default == "0.05"
    assert "ValueError" in fn.raises
    assert fn.docstring == "Calculates sale tax."


def test_parse_class_and_methods():
    code = """
class DatabaseClient:
    '''Postgres DB client.'''
    def __init__(self, dsn: str):
        self.dsn = dsn

    async def query(self, sql: str) -> list:
        return []
"""
    parser = PythonParser()
    module = parser.parse_code(code, module_name="db")

    assert len(module.classes) == 1
    cls = module.classes[0]
    assert cls.name == "DatabaseClient"
    assert len(cls.methods) == 2

    init_m = next(m for m in cls.methods if m.name == "__init__")
    assert init_m.parameters[1].name == "dsn"

    query_m = next(m for m in cls.methods if m.name == "query")
    assert query_m.is_async is True
    assert query_m.return_type == "list"


def test_syntax_error_handling():
    invalid_code = "def broken_syntax(:"
    parser = PythonParser()
    try:
        parser.parse_code(invalid_code)
        assert False, "Should have raised ParsingError"
    except ParsingError:
        pass