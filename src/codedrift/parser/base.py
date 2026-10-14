"""
Abstract Base Parser Interface for CodeDrift.
Allows multi-language and multi-contract parser extensibility.
"""
from abc import ABC, abstractmethod
from typing import Union
from pathlib import Path
from ..core.models import ModuleInfo


class BaseParser(ABC):
    """
    Abstract contract parser for source files.
    """

    @abstractmethod
    def parse_file(self, file_path: Union[str, Path]) -> ModuleInfo:
        """Parses a source file from disk into a ModuleInfo domain entity."""
        pass

    @abstractmethod
    def parse_code(
        self,
        code: str,
        file_path: str = "<memory>",
        module_name: str = "<module>",
    ) -> ModuleInfo:
        """Parses source code from string memory into a ModuleInfo domain entity."""
        pass
