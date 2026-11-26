
import pytest

from codedrift.parser.package_parser import (
    PackageParser,
)


def write_source(root, relative_path, content):

    file_path = root / relative_path

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path.write_text(
        content,
        encoding="utf-8",
    )

    return file_path


def test_qualified_module_name(tmp_path):

    file_path = write_source(
        tmp_path,
        "flask/json/provider.py",
        "def loads(): pass",
    )

    result = PackageParser.get_module_name(
        file_path,
        tmp_path,
    )

    assert result == "flask.json.provider"


def test_init_module_name(tmp_path):

    file_path = write_source(
        tmp_path,
        "flask/__init__.py",
        "def create_app(): pass",
    )

    result = PackageParser.get_module_name(
        file_path,
        tmp_path,
    )

    assert result == "flask"


def test_duplicate_filenames(tmp_path):

    write_source(
        tmp_path,
        "flask/app.py",
        "def run(): pass",
    )

    write_source(
        tmp_path,
        "flask/sansio/app.py",
        "def run(): pass",
    )

    result = PackageParser().parse_package(
        tmp_path
    )

    names = {
        module.module_name
        for module in result.modules
    }

    assert names == {
        "flask.app",
        "flask.sansio.app",
    }

    assert not result.errors


def test_public_function_filter(tmp_path):

    write_source(
        tmp_path,
        "demo/helpers.py",
        "def public_function(): pass\n"
        "def _private_function(): pass\n",
    )

    result = PackageParser().parse_package(
        tmp_path
    )

    functions = result.modules[0].functions

    assert len(functions) == 1

    assert functions[0].qualified_name == (
        "demo.helpers.public_function"
    )


def test_public_class_filter(tmp_path):

    write_source(
        tmp_path,
        "demo/models.py",
        "class PublicClass:\n"
        "    pass\n"
        "class _PrivateClass:\n"
        "    pass\n",
    )

    result = PackageParser().parse_package(
        tmp_path
    )

    classes = result.modules[0].classes

    assert len(classes) == 1

    assert classes[0].name == "PublicClass"


def test_constructor_preserved(tmp_path):

    write_source(
        tmp_path,
        "demo/models.py",
        "class Calculator:\n"
        "    def __init__(self): pass\n"
        "    def add(self): pass\n"
        "    def _validate(self): pass\n",
    )

    result = PackageParser().parse_package(
        tmp_path
    )

    methods = result.modules[0].classes[0].methods

    names = {
        method.name
        for method in methods
    }

    assert names == {
        "__init__",
        "add",
    }


def test_include_private(tmp_path):

    write_source(
        tmp_path,
        "demo/helpers.py",
        "def public_function(): pass\n"
        "def _private_function(): pass\n",
    )

    result = PackageParser().parse_package(
        tmp_path,
        public_only=False,
    )

    assert len(
        result.modules[0].functions
    ) == 2


def test_parse_error_reported(tmp_path):

    write_source(
        tmp_path,
        "demo/broken.py",
        "def broken(",
    )

    write_source(
        tmp_path,
        "demo/valid.py",
        "def valid(): pass",
    )

    result = PackageParser().parse_package(
        tmp_path
    )

    assert len(result.modules) == 1

    assert len(result.errors) == 1

    assert result.errors[0]["file"] == (
        "demo/broken.py"
    )

    assert result.to_dict()["complete"] is False


def test_python_source_encoding(tmp_path):

    file_path = tmp_path / "demo.py"

    file_path.write_bytes(
        "# coding: latin-1\n"
        "def greet():\n"
        "    return 'caf\xe9'\n".encode("latin-1")
    )

    result = PackageParser().parse_package(
        tmp_path
    )

    assert len(result.modules) == 1

    assert not result.errors


def test_ignored_directories(tmp_path):

    write_source(
        tmp_path,
        "demo/main.py",
        "def run(): pass",
    )

    write_source(
        tmp_path,
        "__pycache__/ignored.py",
        "def ignored(): pass",
    )

    result = PackageParser().parse_package(
        tmp_path
    )

    assert len(result.modules) == 1

    assert result.modules[0].module_name == (
        "demo.main"
    )


def test_package_summary(tmp_path):

    write_source(
        tmp_path,
        "demo/main.py",
        "def run(): pass\n"
        "class App:\n"
        "    def start(self): pass\n",
    )

    result = PackageParser().parse_package(
        tmp_path
    ).to_dict()

    assert result["module_count"] == 1

    assert result["function_count"] == 1

    assert result["class_count"] == 1

    assert result["method_count"] == 1

    assert result["complete"] is True


def test_duplicate_module_identity(tmp_path):

    write_source(
        tmp_path,
        "demo.py",
        "def run(): pass",
    )

    write_source(
        tmp_path,
        "demo/__init__.py",
        "def start(): pass",
    )

    result = PackageParser().parse_package(
        tmp_path
    )

    assert len(result.modules) == 1

    assert len(result.errors) == 1

    assert "Duplicate module name" in (
        result.errors[0]["message"]
    )


def test_missing_source_directory(tmp_path):

    with pytest.raises(NotADirectoryError):

        PackageParser().parse_package(
            tmp_path / "missing"
        )
