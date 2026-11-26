
import argparse
import ast
import json
import os
import tokenize

from dataclasses import dataclass, field
from pathlib import Path


MAX_SOURCE_BYTES = 2 * 1024 * 1024

MAX_SOURCE_FILES = 10000

IGNORED_DIRECTORIES = {
    ".git",
    ".github",
    ".venv",
    "venv",
    "env",
    ".env",
    "__pycache__",
    "node_modules",
    "site-packages",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
}


@dataclass
class SourceFile:

    file_path: str

    source_code: str

    tree: ast.Module

    line_count: int

    def to_dict(self):

        return {
            "file_path": self.file_path,
            "line_count": self.line_count,
        }


@dataclass
class SourceScanResult:

    repository: str

    discovered_files: int = 0

    files: list[SourceFile] = field(
        default_factory=list
    )

    errors: list[dict] = field(
        default_factory=list
    )

    skipped_files: list[dict] = field(
        default_factory=list
    )

    ignored_directories: list[str] = field(
        default_factory=list
    )

    limit_reached: bool = False

    @property
    def complete(self):

        return (
            not self.errors
            and not self.skipped_files
            and not self.limit_reached
        )

    def to_dict(self):

        return {
            "repository": self.repository,

            "discovered_files": self.discovered_files,

            "parsed_files": len(self.files),

            "failed_files": len(self.errors),

            "skipped_file_count": len(
                self.skipped_files
            ),

            "ignored_directory_count": len(
                self.ignored_directories
            ),

            "total_lines": sum(
                file.line_count
                for file in self.files
            ),

            "complete": self.complete,

            "limit_reached": self.limit_reached,

            "files": [
                file.to_dict()
                for file in self.files
            ],

            "errors": self.errors,

            "skipped_files": self.skipped_files,

            "ignored_directories": (
                self.ignored_directories
            ),
        }


class SourceScanner:

    def __init__(
        self,
        max_files=MAX_SOURCE_FILES,
        max_source_bytes=MAX_SOURCE_BYTES,
    ):

        if max_files <= 0:

            raise ValueError(
                "Maximum file count must be positive"
            )

        if max_source_bytes <= 0:

            raise ValueError(
                "Maximum source size must be positive"
            )

        self.max_files = max_files

        self.max_source_bytes = max_source_bytes

    def is_ignored_directory(self, name):

        return (
            name.lower() in IGNORED_DIRECTORIES
            or name.startswith(".")
        )

    def scan_repository(self, repository_path):

        root = Path(repository_path).resolve()

        if not root.is_dir():

            raise NotADirectoryError(
                f"Repository not found: {root}"
            )

        result = SourceScanResult(
            repository=root.name
        )

        def record_walk_error(error):

            result.errors.append({
                "file": str(error.filename),
                "error_type": type(error).__name__,
                "message": str(error),
            })

        for directory, subdirectories, filenames in os.walk(
            root,
            topdown=True,
            followlinks=False,
            onerror=record_walk_error,
        ):

            current_directory = Path(directory)

            allowed_directories = []

            for name in sorted(subdirectories):

                path = current_directory / name

                relative_path = (
                    path.relative_to(root).as_posix()
                )

                if (
                    self.is_ignored_directory(name)
                    or path.is_symlink()
                    or (
                        hasattr(path, "is_junction")
                        and path.is_junction()
                    )
                    or not path.resolve().is_relative_to(root)
                ):

                    result.ignored_directories.append(
                        relative_path
                    )

                else:

                    allowed_directories.append(name)

            subdirectories[:] = allowed_directories

            for filename in sorted(filenames):

                if not filename.endswith(".py"):

                    continue

                if result.discovered_files >= self.max_files:

                    result.limit_reached = True

                    return result

                result.discovered_files += 1

                path = current_directory / filename

                relative_path = (
                    path.relative_to(root).as_posix()
                )

                try:

                    if path.is_symlink():

                        result.skipped_files.append({
                            "file": relative_path,
                            "reason": "symbolic_link",
                        })

                        continue

                    if not path.resolve().is_relative_to(root):

                        result.skipped_files.append({
                            "file": relative_path,
                            "reason": "outside_repository",
                        })

                        continue

                    if not path.is_file():

                        result.skipped_files.append({
                            "file": relative_path,
                            "reason": "not_regular_file",
                        })

                        continue

                    if path.stat().st_size > self.max_source_bytes:

                        result.skipped_files.append({
                            "file": relative_path,
                            "reason": "file_too_large",
                        })

                        continue

                    with tokenize.open(path) as source:

                        code = source.read(
                            self.max_source_bytes + 1
                        )

                    if len(code) > self.max_source_bytes:

                        result.skipped_files.append({
                            "file": relative_path,
                            "reason": "file_too_large",
                        })

                        continue

                    tree = ast.parse(
                        code,
                        filename=relative_path,
                    )

                    result.files.append(
                        SourceFile(
                            file_path=relative_path,
                            source_code=code,
                            tree=tree,
                            line_count=len(
                                code.splitlines()
                            ),
                        )
                    )

                except (
                    OSError,
                    SyntaxError,
                    UnicodeError,
                    ValueError,
                    RecursionError,
                    LookupError,
                ) as error:

                    result.errors.append({
                        "file": relative_path,
                        "error_type": type(error).__name__,
                        "message": str(error),
                    })

        return result


def main():

    parser = argparse.ArgumentParser(
        description="CodeDrift application source scanner"
    )

    parser.add_argument(
        "repository",
        help="Local repository directory",
    )

    parser.add_argument(
        "--max-files",
        type=int,
        default=MAX_SOURCE_FILES,
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Display summary without file listing",
    )

    args = parser.parse_args()

    try:

        scanner = SourceScanner(
            max_files=args.max_files
        )

        result = scanner.scan_repository(
            args.repository
        )

        report = result.to_dict()

        if args.summary:

            report.pop("files")

        print(json.dumps(report, indent=2))

        return 0 if result.complete else 1

    except (OSError, ValueError) as error:

        parser.exit(
            status=1,
            message=f"CodeDrift error: {error}\n",
        )


if __name__ == "__main__":

    raise SystemExit(main())
