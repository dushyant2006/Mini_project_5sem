from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class ParameterInfo:
    name: str
    kind: str
    annotation: Optional[str] = None
    default: Optional[str] = None


@dataclass
class FunctionInfo:
    name: str
    qualified_name: str
    signature: str
    parameters: list[ParameterInfo]
    return_type: Optional[str]
    visibility: str
    decorators: list[str]
    raises: list[str]
    is_async: bool
    line: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ClassInfo:
    name: str
    qualified_name: str
    bases: list[str]
    visibility: str
    decorators: list[str]
    methods: list[FunctionInfo]
    line: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ImportInfo:
    module: str
    name: Optional[str]
    alias: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ModuleInfo:
    module_name: str
    file_path: str
    imports: list[ImportInfo]
    functions: list[FunctionInfo]
    classes: list[ClassInfo]

    def to_dict(self) -> dict:
        return asdict(self)