"""
Static Call Graph Builder and AST Symbol Resolver.
Scans client Python code to detect all function and method invocations,
resolving them against imported third-party library modules.
"""
import ast
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
from ..core.models import CallSite


class CallGraphVisitor(ast.NodeVisitor):
    """
    AST visitor that collects function and method call sites and resolves their target symbols.
    """

    def __init__(self, file_path: str, code_lines: List[str], target_packages: Optional[Set[str]] = None):
        self.file_path = file_path
        self.code_lines = code_lines
        self.target_packages = target_packages or set()

        # Import alias maps:
        # e.g. "from paymentlib import process_payment" -> {"process_payment": "paymentlib.process_payment"}
        # e.g. "import paymentlib as p" -> {"p": "paymentlib"}
        self.symbol_map: Dict[str, str] = {}
        self.module_alias_map: Dict[str, str] = {}

        self.current_function: Optional[str] = None
        self.call_sites: List[CallSite] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            alias_name = alias.asname or alias.name
            self.module_alias_map[alias_name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        for alias in node.names:
            alias_name = alias.asname or alias.name
            self.symbol_map[alias_name] = f"{mod}.{alias.name}"
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        prev = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev

    def visit_Call(self, node: ast.Call):
        callee_name, resolved_target = self._resolve_call(node.func)

        # Extract arguments passed as strings
        arg_strings = []
        for arg in node.args:
            try:
                arg_strings.append(ast.unparse(arg))
            except Exception:
                arg_strings.append("<expr>")
        for kw in node.keywords:
            try:
                arg_strings.append(f"{kw.arg}={ast.unparse(kw.value)}")
            except Exception:
                arg_strings.append(f"{kw.arg}=<expr>")

        line_no = getattr(node, "lineno", 1)
        col_offset = getattr(node, "col_offset", 0)
        snippet = self.code_lines[line_no - 1].strip() if 0 < line_no <= len(self.code_lines) else ""

        call_site = CallSite(
            file_path=self.file_path,
            line=line_no,
            column=col_offset,
            caller_function=self.current_function,
            callee_name=callee_name,
            matched_target=resolved_target or callee_name,
            code_snippet=snippet,
            arguments_passed=arg_strings,
        )
        self.call_sites.append(call_site)
        self.generic_visit(node)

    def _resolve_call(self, func_node: ast.AST) -> tuple[str, Optional[str]]:
        """
        Resolves AST func node to (display_name, fully_qualified_target)
        """
        if isinstance(func_node, ast.Name):
            callee_name = func_node.id
            resolved = self.symbol_map.get(callee_name, None)
            return callee_name, resolved

        elif isinstance(func_node, ast.Attribute):
            attr_name = func_node.attr
            # Check receiver: e.g. client.process_payment or paymentlib.process_payment
            if isinstance(func_node.value, ast.Name):
                receiver = func_node.value.id
                if receiver in self.module_alias_map:
                    real_mod = self.module_alias_map[receiver]
                    return f"{receiver}.{attr_name}", f"{real_mod}.{attr_name}"
                elif receiver in self.symbol_map:
                    mapped = self.symbol_map[receiver]
                    return f"{receiver}.{attr_name}", f"{mapped}.{attr_name}"
                return f"{receiver}.{attr_name}", None
            elif isinstance(func_node.value, ast.Attribute):
                # Chain like a.b.c
                try:
                    chain = ast.unparse(func_node)
                    return chain, None
                except Exception:
                    return attr_name, None
            return attr_name, None

        return "<callable>", None


class CallGraphBuilder:
    """
    Builds static call graphs for downstream client repositories.
    """

    def scan_file(
        self,
        file_path: Union[str, Path],
        target_packages: Optional[Set[str]] = None,
    ) -> List[CallSite]:
        path = Path(file_path)
        if not path.is_file() or path.suffix != ".py":
            return []

        try:
            code = path.read_text(encoding="utf-8")
        except Exception:
            return []

        lines = code.splitlines()
        try:
            tree = ast.parse(code, filename=str(path))
        except SyntaxError:
            return []

        visitor = CallGraphVisitor(
            file_path=str(path),
            code_lines=lines,
            target_packages=target_packages,
        )
        visitor.visit(tree)
        return visitor.call_sites

    def scan_directory(
        self,
        directory: Union[str, Path],
        target_packages: Optional[Set[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
    ) -> List[CallSite]:
        dir_path = Path(directory)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Client directory not found: {directory}")

        all_sites: List[CallSite] = []
        for file in sorted(dir_path.rglob("*.py")):
            rel_str = str(file.relative_to(dir_path))
            # Basic ignore filters
            if any(part.startswith((".", "__pycache__", "venv", ".venv")) for part in file.parts):
                continue
            all_sites.extend(self.scan_file(file, target_packages=target_packages))

        return all_sites
