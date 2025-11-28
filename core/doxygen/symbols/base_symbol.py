"""
Base symbol class for representing C++ code entities.
"""

from abc import ABC
from typing import Set
from pathlib import Path

from .symbol_kind import SymbolKind


class BaseSymbol(ABC):
    """
    Abstract base class for C++ symbols extracted from source parsing.

    Contains common attributes shared by all symbol types (functions, classes, enums, etc.).
    """

    def __init__(self, kind: SymbolKind):
        self.kind: SymbolKind = kind
        self.name: str = ''
        self.qualified_name: str = ''
        self.file_path: str = ''
        self.line_start: int = 0
        self.line_end: int = 0
        self.prototype: str = ''
        self.dependencies: Set[str] = set()
        self.doxygen_id: str = ''

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.kind.value}: {self.qualified_name} at {self.file_path}:{self.line_start}-{self.line_end})"

    def get_file_path(self) -> Path:
        """Return file path as Path object."""
        return Path(self.file_path) if self.file_path else Path()
