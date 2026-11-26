
import argparse
import json
import tokenize

from dataclasses import dataclass, field, replace
from pathlib import Path

from ..core.models import ModuleInfo
from .python_parser import PythonParser


MAX_SOURCE_BYTES = 2 * 1024 * 1024

MAX_PYTHON_FILES = 10000

IGNORED_DIRECTORIES = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    ".pytest_cache",
}


@dataclass
class PackageParseResult:

    modules: list[ModuleInfo] = field(default_factory=list)

    errors: list[dict] = field(default_factory=list)

    skipped_files: list[str] = field(default_factory=list)

    discovered_files: int = 0

    def to_dict(self):

        return {
            "discovered_files": self.discovered_files,
            "module_count": len(self.modules),
            "failed_files": len(self.errors),
            "skipped_file_count": len(self.skipped_files),
            "function_count": sum(
                len(module.functions)
                for module in self.modules
            ),
            "class_count": sum(
                len(module.classes)
                for module in self.modules
            ),
            "method_count": sum(
                len(cls.methods)
                for module in self.modules
                for cls in module.classes
            ),
            "complete": (
                not self.errors
                and not self.skipped_files
                and bool(self.modules)
            ),
            "errors": self.errors,
            "skipped_files": self.skipped_files,
            "modules": [
                module.to_dict()
                for module in self.modules
            ],
        }


class PackageParser:

    def __init__(self):

        self.parser = PythonParser()

    @staticmethod
    def get_module_name(file_path, source_root):

        file_path = Path(file_path).resolve()

        source_root = Path(source_root).resolve()

        relative_path = file_path.relative_to(
            source_root
        )

        if relative_path.suffix != ".py":

            raise ValueError(
                "Expected a Python source file"
            )

        parts = list(
            relative_path.with_suffix("").parts
        )

        if parts[-1] == "__init__":

            parts.pop()

        if not parts:

            raise ValueError(
                "Unable to determine package module name"
            )

        if not all(
            part.isidentifier()
            for part in parts
        ):

            raise ValueError(
                "Invalid Python module path"
            )

        return ".".join(parts)

    @staticmethod
    def filter_public_api(module):

        functions = [
            function
            for function in module.functions
            if function.visibility == "public"
        ]

        classes = []

        for cls in module.classes:

            if cls.visibility != "public":
                continue

            methods = [
                method
                for method in cls.methods
                if method.visibility in (
                    "public",
                    "magic",
                )
            ]

            classes.append(
                replace(
                    cls,
                    methods=methods,
                )
            )

        return replace(
            module,
            functions=functions,
            classes=classes,
        )

    @staticmethod
    def is_ignored(file_path, source_root):

        relative_path = file_path.relative_to(
            source_root
        )

        return any(
            part in IGNORED_DIRECTORIES
            or part.startswith(".")
            for part in relative_path.parts
        )

    def parse_package(
        self,
        source_root,
        public_only=True,
    ):

        source_root = Path(source_root).resolve()

        if not source_root.is_dir():

            raise NotADirectoryError(
                f"Source directory not found: {source_root}"
            )

        result = PackageParseResult()

        seen_modules = set()

        python_files = []

        for file_path in source_root.rglob("*.py"):

            python_files.append(file_path)

            if len(python_files) > MAX_PYTHON_FILES:

                raise ValueError(
                    "Python file count limit exceeded"
                )

        python_files.sort()

        result.discovered_files = len(python_files)

        for file_path in python_files:

            relative_path = file_path.relative_to(
                source_root
            ).as_posix()

            if self.is_ignored(
                file_path,
                source_root,
            ):
                continue

            try:

                if (
                    file_path.is_symlink()
                    or not file_path.is_file()
                    or not file_path.resolve().is_relative_to(
                        source_root
                    )
                ):

                    result.skipped_files.append(
                        relative_path
                    )

                    continue

                if file_path.stat().st_size > MAX_SOURCE_BYTES:

                    result.skipped_files.append(
                        relative_path
                    )

                    continue

                module_name = self.get_module_name(
                    file_path,
                    source_root,
                )

                if module_name in seen_modules:

                    raise ValueError(
                        f"Duplicate module name: {module_name}"
                    )

                with tokenize.open(file_path) as source:

                    code = source.read()

                module = self.parser.parse_code(
                    code=code,
                    file_path=relative_path,
                    module_name=module_name,
                )

                if public_only:

                    module = self.filter_public_api(
                        module
                    )

                result.modules.append(module)

                seen_modules.add(module_name)

            except Exception as error:

                result.errors.append({
                    "file": relative_path,
                    "error_type": type(error).__name__,
                    "message": str(error),
                })

        return result


def main():

    parser = argparse.ArgumentParser(
        description="CodeDrift package API parser"
    )

    parser.add_argument("source_root")

    parser.add_argument(
        "--include-private",
        action="store_true",
        help="Include private functions and classes",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary without full API contracts",
    )

    args = parser.parse_args()

    try:

        package_parser = PackageParser()

        result = package_parser.parse_package(
            args.source_root,
            public_only=not args.include_private,
        )

        report = result.to_dict()

        if args.summary:

            report.pop("modules")

        print(json.dumps(report, indent=2))

        return 0 if report["complete"] else 1

    except (OSError, ValueError) as error:

        parser.exit(
            status=1,
            message=f"CodeDrift error: {error}\n",
        )


if __name__ == "__main__":

    raise SystemExit(main())
