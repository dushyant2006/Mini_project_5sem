import ast
from pathlib import Path
from typing import Optional

from .models import (
    ClassInfo,
    FunctionInfo,
    ImportInfo,
    ModuleInfo,
    ParameterInfo,
)


class PythonParser:
    """
    Extracts API-level information from Python source code using AST.

    CodeDrift uses this information later to compare two library versions
    and detect syntactic and behavioral compatibility changes.
    """

    def parse_file(self, file_path: str) -> ModuleInfo:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Python file not found: {file_path}")

        if path.suffix != ".py":
            raise ValueError(f"Expected a Python file, got: {path.suffix}")

        code = path.read_text(encoding="utf-8")
        module_name = path.stem

        return self.parse_code(
            code=code,
            file_path=str(path),
            module_name=module_name,
        )

    def parse_code(
        self,
        code: str,
        file_path: str = "<memory>",
        module_name: str = "<module>",
    ) -> ModuleInfo:

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            raise ValueError(
                f"Unable to parse Python source: "
                f"line {exc.lineno}, column {exc.offset}: {exc.msg}"
            ) from exc

        imports = self._extract_imports(tree)
        functions = []
        classes = []

        for node in tree.body:

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(
                    self._extract_function(
                        node=node,
                        qualified_name=f"{module_name}.{node.name}",
                    )
                )

            elif isinstance(node, ast.ClassDef):
                classes.append(
                    self._extract_class(
                        node=node,
                        module_name=module_name,
                    )
                )

        return ModuleInfo(
            module_name=module_name,
            file_path=file_path,
            imports=imports,
            functions=functions,
            classes=classes,
        )

    def _extract_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        qualified_name: str,
    ) -> FunctionInfo:

        parameters = self._extract_parameters(node.args)
        return_type = self._annotation_to_string(node.returns)
        decorators = [
            self._node_to_string(decorator)
            for decorator in node.decorator_list
        ]

        raises = self._extract_raised_exceptions(node)

        return FunctionInfo(
            name=node.name,
            qualified_name=qualified_name,
            signature=self._build_signature(node),
            parameters=parameters,
            return_type=return_type,
            visibility=self._get_visibility(node.name),
            decorators=decorators,
            raises=raises,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            line=node.lineno,
        )

    def _extract_class(
        self,
        node: ast.ClassDef,
        module_name: str,
    ) -> ClassInfo:

        methods = []

        for child in node.body:

            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(
                    self._extract_function(
                        node=child,
                        qualified_name=(
                            f"{module_name}.{node.name}.{child.name}"
                        ),
                    )
                )

        bases = [
            self._node_to_string(base)
            for base in node.bases
        ]

        decorators = [
            self._node_to_string(decorator)
            for decorator in node.decorator_list
        ]

        return ClassInfo(
            name=node.name,
            qualified_name=f"{module_name}.{node.name}",
            bases=bases,
            visibility=self._get_visibility(node.name),
            decorators=decorators,
            methods=methods,
            line=node.lineno,
        )

    def _extract_parameters(
        self,
        args: ast.arguments,
    ) -> list[ParameterInfo]:

        parameters = []

        positional_count = len(args.posonlyargs)
        normal_count = len(args.args)

        defaults = [None] * (
            positional_count + normal_count - len(args.defaults)
        )

        defaults.extend(args.defaults)

        all_positional = args.posonlyargs + args.args

        for index, argument in enumerate(all_positional):

            default = None

            if defaults[index] is not None:
                default = self._node_to_string(defaults[index])

            parameters.append(
                ParameterInfo(
                    name=argument.arg,
                    kind=(
                        "positional_only"
                        if index < positional_count
                        else "positional_or_keyword"
                    ),
                    annotation=self._annotation_to_string(
                        argument.annotation
                    ),
                    default=default,
                )
            )

        if args.vararg is not None:
            parameters.append(
                ParameterInfo(
                    name=args.vararg.arg,
                    kind="var_positional",
                    annotation=self._annotation_to_string(
                        args.vararg.annotation
                    ),
                )
            )

        for argument, default in zip(
            args.kwonlyargs,
            args.kw_defaults,
        ):
            parameters.append(
                ParameterInfo(
                    name=argument.arg,
                    kind="keyword_only",
                    annotation=self._annotation_to_string(
                        argument.annotation
                    ),
                    default=(
                        self._node_to_string(default)
                        if default is not None
                        else None
                    ),
                )
            )

        if args.kwarg is not None:
            parameters.append(
                ParameterInfo(
                    name=args.kwarg.arg,
                    kind="var_keyword",
                    annotation=self._annotation_to_string(
                        args.kwarg.annotation
                    ),
                )
            )

        return parameters

    def _build_signature(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> str:

        prefix = "async def" if isinstance(
            node,
            ast.AsyncFunctionDef,
        ) else "def"

        return_annotation = self._annotation_to_string(node.returns)

        parameters = self._build_signature_parameters(node.args)

        signature = f"{prefix} {node.name}({parameters})"

        if return_annotation:
            signature += f" -> {return_annotation}"

        return signature

    def _build_signature_parameters(
        self,
        args: ast.arguments,
    ) -> str:

        parts = []

        posonly = args.posonlyargs
        normal = args.args

        total_positional = len(posonly) + len(normal)
        defaults_start = total_positional - len(args.defaults)

        for index, argument in enumerate(posonly):

            default = None

            if index >= defaults_start:
                default_index = index - defaults_start
                default = args.defaults[default_index]

            parts.append(
                self._format_parameter(
                    argument,
                    default,
                )
            )

        if posonly:
            parts.append("/")

        for index, argument in enumerate(normal):

            global_index = len(posonly) + index
            default = None

            if global_index >= defaults_start:
                default_index = global_index - defaults_start
                default = args.defaults[default_index]

            parts.append(
                self._format_parameter(
                    argument,
                    default,
                )
            )

        if args.vararg:
            parts.append(
                "*" + self._format_parameter(args.vararg)
            )
        elif args.kwonlyargs:
            parts.append("*")

        for argument, default in zip(
            args.kwonlyargs,
            args.kw_defaults,
        ):
            parts.append(
                self._format_parameter(
                    argument,
                    default,
                )
            )

        if args.kwarg:
            parts.append(
                "**" + self._format_parameter(args.kwarg)
            )

        return ", ".join(parts)

    def _format_parameter(
        self,
        argument: ast.arg,
        default: Optional[ast.expr] = None,
    ) -> str:

        result = argument.arg

        annotation = self._annotation_to_string(argument.annotation)

        if annotation:
            result += f": {annotation}"

        if default is not None:
            result += f" = {self._node_to_string(default)}"

        return result

    def _extract_imports(
        self,
        tree: ast.Module,
    ) -> list[ImportInfo]:

        imports = []

        for node in tree.body:

            if isinstance(node, ast.Import):

                for alias in node.names:
                    imports.append(
                        ImportInfo(
                            module=alias.name,
                            name=None,
                            alias=alias.asname,
                        )
                    )

            elif isinstance(node, ast.ImportFrom):

                module = node.module or ""

                for alias in node.names:
                    imports.append(
                        ImportInfo(
                            module=module,
                            name=alias.name,
                            alias=alias.asname,
                        )
                    )

        return imports

    def _extract_raised_exceptions(
        self,
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[str]:

        exceptions = []

        for node in ast.walk(function_node):

            if node is function_node:
                continue

            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            ):
                continue

            if isinstance(node, ast.Raise):

                if node.exc is None:
                    exceptions.append("re-raise")
                    continue

                exceptions.append(
                    self._node_to_string(node.exc)
                )

        return sorted(set(exceptions))

    def _get_visibility(self, name: str) -> str:

        if name.startswith("__") and name.endswith("__"):
            return "magic"

        if name.startswith("_"):
            return "private"

        return "public"

    def _annotation_to_string(
        self,
        node: Optional[ast.expr],
    ) -> Optional[str]:

        if node is None:
            return None

        return self._node_to_string(node)

    @staticmethod
    def _node_to_string(node: ast.AST) -> str:

        return ast.unparse(node)