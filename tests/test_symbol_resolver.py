
import ast

from codedrift.impact.source_scanner import SourceFile

from codedrift.impact.symbol_resolver import (
    SymbolResolver,
    resolve_repository,
)


def resolve(code, packages=None):

    source = SourceFile(
        file_path="app.py",
        source_code=code,
        tree=ast.parse(code),
        line_count=len(code.splitlines()),
    )

    resolver = SymbolResolver(
        source,
        target_packages=packages,
    )

    return resolver.resolve()


def test_direct_import():

    calls = resolve(
        "import requests\n"
        "requests.get(url)\n"
    )

    assert len(calls) == 1

    assert (
        calls[0].qualified_name
        == "requests.get"
    )


def test_aliased_import():

    calls = resolve(
        "import requests as r\n"
        "r.get(url)\n"
    )

    assert len(calls) == 1

    assert (
        calls[0].qualified_name
        == "requests.get"
    )


def test_from_import():

    calls = resolve(
        "from requests import get\n"
        "get(url)\n"
    )

    assert (
        calls[0].qualified_name
        == "requests.get"
    )


def test_aliased_from_import():

    calls = resolve(
        "from requests import get as fetch\n"
        "fetch(url)\n"
    )

    assert (
        calls[0].qualified_name
        == "requests.get"
    )


def test_nested_module_import():

    calls = resolve(
        "import flask.json\n"
        "flask.json.dumps(data)\n"
    )

    assert (
        calls[0].qualified_name
        == "flask.json.dumps"
    )


def test_nested_aliased_module():

    calls = resolve(
        "import flask.json as fj\n"
        "fj.dumps(data)\n"
    )

    assert (
        calls[0].qualified_name
        == "flask.json.dumps"
    )


def test_imported_class():

    calls = resolve(
        "from jinja2 import Environment\n"
        "Environment()\n"
    )

    assert (
        calls[0].qualified_name
        == "jinja2.Environment"
    )


def test_package_filter():

    calls = resolve(
        "import requests\n"
        "import flask\n"
        "requests.get(url)\n"
        "flask.Flask(__name__)\n",
        packages={"requests"},
    )

    assert len(calls) == 1

    assert calls[0].package == "requests"


def test_exact_package_filter():

    calls = resolve(
        "import requests_extra\n"
        "requests_extra.get(url)\n",
        packages={"requests"},
    )

    assert calls == []


def test_unrelated_function():

    calls = resolve(
        "def get(url):\n"
        "    return url\n"
        "get(url)\n"
    )

    assert calls == []


def test_argument_extraction():

    calls = resolve(
        "import requests\n"
        "requests.get(url, timeout=10)\n"
    )

    assert calls[0].positional_arguments == [
        "url"
    ]

    assert calls[0].keyword_arguments == {
        "timeout": "10"
    }


def test_expanded_arguments():

    calls = resolve(
        "import requests\n"
        "requests.get(*args, **kwargs)\n"
    )

    assert calls[0].has_starred_arguments

    assert calls[0].has_expanded_keywords


def test_variable_shadowing():

    calls = resolve(
        "import requests as r\n"
        "r = local_object\n"
        "r.get(url)\n"
    )

    assert calls == []


def test_parameter_shadowing():

    calls = resolve(
        "import requests as r\n"
        "def fetch(r):\n"
        "    r.get(url)\n"
    )

    assert calls == []


def test_local_assignment_shadowing():

    calls = resolve(
        "import requests as r\n"
        "def fetch():\n"
        "    r.get(url)\n"
        "    r = local_object\n"
    )

    assert calls == []


def test_local_import():

    calls = resolve(
        "def fetch():\n"
        "    import requests as r\n"
        "    r.get(url)\n"
    )

    assert len(calls) == 1

    assert (
        calls[0].qualified_name
        == "requests.get"
    )

    assert calls[0].caller_function == "fetch"


def test_function_scope_isolation():

    calls = resolve(
        "def fetch():\n"
        "    import requests as r\n"
        "    r.get(url)\n"
        "r.get(url)\n"
    )

    assert len(calls) == 1


def test_relative_import_not_external():

    calls = resolve(
        "from .requests import get\n"
        "get(url)\n"
    )

    assert calls == []


def test_line_number_and_file_path():

    calls = resolve(
        "import requests\n"
        "\n"
        "requests.get(url)\n"
    )

    assert calls[0].line == 3

    assert calls[0].file_path == "app.py"


def test_repository_resolution(tmp_path):

    (tmp_path / "app.py").write_text(
        "import requests as r\n"
        "r.get(url)\n"
        "r.post(url)\n",
        encoding="utf-8",
    )

    report = resolve_repository(
        tmp_path,
        target_packages={"requests"},
    )

    assert report["resolved_calls"] == 2

    assert report["package_count"] == 1

    assert report["unique_symbol_count"] == 2

    assert report["source_scan"]["complete"]

    assert report["packages"] == ["requests"]


def test_unsupported_control_flow_warning(tmp_path):

    (tmp_path / "app.py").write_text(
        "import requests\n"
        "if condition:\n"
        "    requests.get(url)\n",
        encoding="utf-8",
    )

    report = resolve_repository(
        tmp_path,
        target_packages={"requests"},
    )

    assert report["warning_count"] == 1

    assert report["resolved_calls"] == 0
