
import argparse
import ast
import json

from dataclasses import asdict, dataclass, field

from .source_scanner import SourceScanner, SourceFile


@dataclass
class ResolvedCall:

    file_path: str

    line: int

    column: int

    caller_function: str | None

    callee_name: str

    qualified_name: str

    package: str

    positional_arguments: list[str] = field(
        default_factory=list
    )

    keyword_arguments: dict[str, str] = field(
        default_factory=dict
    )

    has_starred_arguments: bool = False

    has_expanded_keywords: bool = False

    code_snippet: str = ""

    def to_dict(self):

        return asdict(self)


class LocalBindingCollector(ast.NodeVisitor):

    def __init__(self):

        self.names = set()

        self.unsupported_scope = False

    def visit_Name(self, node):

        if isinstance(node.ctx, (ast.Store, ast.Del)):

            self.names.add(node.id)

    def visit_Import(self, node):

        for alias in node.names:

            self.names.add(
                alias.asname or alias.name.split(".")[0]
            )

    def visit_ImportFrom(self, node):

        for alias in node.names:

            self.names.add(
                alias.asname or alias.name
            )

    def visit_FunctionDef(self, node):

        self.names.add(node.name)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):

        self.names.add(node.name)

    def visit_Global(self, node):

        self.unsupported_scope = True

    def visit_Nonlocal(self, node):

        self.unsupported_scope = True

    def visit_ExceptHandler(self, node):

        if node.name:

            self.names.add(node.name)

        self.generic_visit(node)

    def visit_MatchAs(self, node):

        if node.name:

            self.names.add(node.name)

        self.generic_visit(node)

    def visit_MatchStar(self, node):

        if node.name:

            self.names.add(node.name)

    def visit_MatchMapping(self, node):

        if node.rest:

            self.names.add(node.rest)

        self.generic_visit(node)


class SymbolResolver(ast.NodeVisitor):

    def __init__(
        self,
        source_file: SourceFile,
        target_packages=None,
    ):

        self.source_file = source_file

        self.code_lines = (
            source_file.source_code.splitlines()
        )

        self.target_packages = (
            set(target_packages)
            if target_packages is not None
            else None
        )

        self.bindings = {}

        self.function_stack = []

        self.calls = []

        self.warnings = []

    def warn(self, node, reason):

        self.warnings.append({
            "file": self.source_file.file_path,
            "line": getattr(node, "lineno", 1),
            "reason": reason,
        })

    def resolve_expression(self, node):

        if isinstance(node, ast.Name):

            return self.bindings.get(node.id)

        if isinstance(node, ast.Attribute):

            parent = self.resolve_expression(
                node.value
            )

            if parent:

                return f"{parent}.{node.attr}"

        return None

    def invalidate_target(self, target):

        if isinstance(target, ast.Name):

            self.bindings.pop(target.id, None)

        elif isinstance(target, (ast.Tuple, ast.List)):

            for element in target.elts:

                self.invalidate_target(element)

        elif isinstance(target, ast.Starred):

            self.invalidate_target(target.value)

        elif isinstance(target, ast.Attribute):

            root = target

            while isinstance(root, ast.Attribute):

                root = root.value

            if isinstance(root, ast.Name):

                self.bindings.pop(root.id, None)

    def visit_Import(self, node):

        for alias in node.names:

            if alias.asname:

                self.bindings[alias.asname] = (
                    alias.name
                )

            else:

                root = alias.name.split(".")[0]

                self.bindings[root] = root

    def visit_ImportFrom(self, node):

        for alias in node.names:

            local_name = alias.asname or alias.name

            if alias.name == "*":

                self.bindings.clear()

                self.warn(
                    node,
                    "Wildcard import is not resolved",
                )

                continue

            if node.level or not node.module:

                self.bindings.pop(local_name, None)

                continue

            self.bindings[local_name] = (
                f"{node.module}.{alias.name}"
            )

    def visit_Assign(self, node):

        self.visit(node.value)

        for target in node.targets:

            self.invalidate_target(target)

    def visit_AnnAssign(self, node):

        if node.value is not None:

            self.visit(node.value)

            self.invalidate_target(node.target)

    def visit_AugAssign(self, node):

        self.visit(node.value)

        self.invalidate_target(node.target)

    def visit_Delete(self, node):

        for target in node.targets:

            self.invalidate_target(target)

    def visit_NamedExpr(self, node):

        self.visit(node.value)

        self.invalidate_target(node.target)

    def visit_FunctionDef(self, node):

        for decorator in node.decorator_list:

            self.visit(decorator)

        for default in node.args.defaults:

            self.visit(default)

        for default in node.args.kw_defaults:

            if default is not None:

                self.visit(default)

        outer_bindings = self.bindings

        outer_bindings.pop(node.name, None)

        collector = LocalBindingCollector()

        for statement in node.body:

            collector.visit(statement)

        if collector.unsupported_scope:

            self.warn(
                node,
                "Global or nonlocal scope is not resolved",
            )

            return

        local_names = collector.names

        parameters = (
            node.args.posonlyargs
            + node.args.args
            + node.args.kwonlyargs
        )

        for parameter in parameters:

            local_names.add(parameter.arg)

        if node.args.vararg:

            local_names.add(node.args.vararg.arg)

        if node.args.kwarg:

            local_names.add(node.args.kwarg.arg)

        self.bindings = {
            name: value
            for name, value in outer_bindings.items()
            if name not in local_names
        }

        self.function_stack.append(node.name)

        try:

            for statement in node.body:

                self.visit(statement)

        finally:

            self.function_stack.pop()

            self.bindings = outer_bindings

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):

        for decorator in node.decorator_list:

            self.visit(decorator)

        for base in node.bases:

            self.visit(base)

        self.bindings.pop(node.name, None)

        self.warn(
            node,
            "Class body resolution is deferred",
        )

    def visit_Lambda(self, node):

        self.warn(
            node,
            "Lambda scope resolution is deferred",
        )

    def visit_ListComp(self, node):

        self.warn(
            node,
            "Comprehension resolution is deferred",
        )

    visit_SetComp = visit_ListComp

    visit_DictComp = visit_ListComp

    visit_GeneratorExp = visit_ListComp

    def visit_control_flow(self, node):

        collector = LocalBindingCollector()

        collector.visit(node)

        for name in collector.names:

            self.bindings.pop(name, None)

        self.warn(
            node,
            "Conditional or repeated execution is not resolved",
        )

    visit_If = visit_control_flow

    visit_For = visit_control_flow

    visit_AsyncFor = visit_control_flow

    visit_While = visit_control_flow

    visit_Try = visit_control_flow

    visit_TryStar = visit_control_flow

    visit_Match = visit_control_flow

    visit_With = visit_control_flow

    visit_AsyncWith = visit_control_flow

    def visit_Call(self, node):

        qualified_name = self.resolve_expression(
            node.func
        )

        if qualified_name:

            package = qualified_name.split(".")[0]

            allowed = (
                self.target_packages is None
                or package in self.target_packages
            )

            if allowed:

                positional_arguments = []

                keyword_arguments = {}

                has_starred_arguments = False

                has_expanded_keywords = False

                for argument in node.args:

                    if isinstance(argument, ast.Starred):

                        has_starred_arguments = True

                    positional_arguments.append(
                        ast.unparse(argument)
                    )

                for keyword in node.keywords:

                    if keyword.arg is None:

                        has_expanded_keywords = True

                    else:

                        keyword_arguments[keyword.arg] = (
                            ast.unparse(keyword.value)
                        )

                line = node.lineno

                snippet = ""

                if 0 < line <= len(self.code_lines):

                    snippet = (
                        self.code_lines[line - 1].strip()
                    )

                caller = (
                    ".".join(self.function_stack)
                    if self.function_stack
                    else None
                )

                self.calls.append(
                    ResolvedCall(
                        file_path=(
                            self.source_file.file_path
                        ),
                        line=line,
                        column=node.col_offset,
                        caller_function=caller,
                        callee_name=ast.unparse(node.func),
                        qualified_name=qualified_name,
                        package=package,
                        positional_arguments=(
                            positional_arguments
                        ),
                        keyword_arguments=(
                            keyword_arguments
                        ),
                        has_starred_arguments=(
                            has_starred_arguments
                        ),
                        has_expanded_keywords=(
                            has_expanded_keywords
                        ),
                        code_snippet=snippet,
                    )
                )

        self.generic_visit(node)

    def resolve(self):

        self.visit(self.source_file.tree)

        return self.calls


def resolve_repository(
    repository_path,
    target_packages=None,
):

    scanner = SourceScanner()

    source_result = scanner.scan_repository(
        repository_path
    )

    calls = []

    warnings = []

    for source_file in source_result.files:

        resolver = SymbolResolver(
            source_file,
            target_packages=target_packages,
        )

        calls.extend(resolver.resolve())

        warnings.extend(resolver.warnings)

    calls.sort(
        key=lambda call: (
            call.file_path,
            call.line,
            call.column,
        )
    )

    packages = sorted({
        call.package
        for call in calls
    })

    unique_symbols = sorted({
        call.qualified_name
        for call in calls
    })

    source_summary = source_result.to_dict()

    source_summary.pop("files")

    return {
        "repository": source_result.repository,

        "analysis_method": "static_ast_import_resolution",

        "source_scan": source_summary,

        "target_packages": (
            sorted(target_packages)
            if target_packages is not None
            else None
        ),

        "resolved_calls": len(calls),

        "package_count": len(packages),

        "packages": packages,

        "unique_symbol_count": len(unique_symbols),

        "unique_symbols": unique_symbols,

        "warning_count": len(warnings),

        "warnings": warnings,

        "calls": [
            call.to_dict()
            for call in calls
        ],
    }


def main():

    parser = argparse.ArgumentParser(
        description="CodeDrift imported API resolver"
    )

    parser.add_argument(
        "repository",
        help="Local repository directory",
    )

    parser.add_argument(
        "--package",
        action="append",
        help="Filter by Python import package name",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
    )

    args = parser.parse_args()

    try:

        report = resolve_repository(
            args.repository,
            target_packages=args.package,
        )

        if args.summary:

            report.pop("calls")

            report.pop("warnings")

        print(json.dumps(report, indent=2))

        return (
            0
            if report["source_scan"]["complete"]
            else 1
        )

    except (OSError, ValueError) as error:

        parser.exit(
            status=1,
            message=f"CodeDrift error: {error}\n",
        )


if __name__ == "__main__":

    raise SystemExit(main())
