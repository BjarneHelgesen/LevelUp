"""
Class and struct symbol representation.
"""

from typing import List

from .base_symbol import BaseSymbol
from .symbol_kind import SymbolKind


class ClassSymbol(BaseSymbol):
    """
    Represents a C++ class or struct symbol.

    Attributes:
        members: List of Doxygen IDs of member functions/variables
        base_classes: List of qualified names of base classes
    """

    def __init__(self, kind: SymbolKind = SymbolKind.CLASS):
        if kind not in (SymbolKind.CLASS, SymbolKind.STRUCT):
            raise ValueError(f"ClassSymbol requires CLASS or STRUCT kind, got {kind}")
        super().__init__(kind)
        self.members: List[str] = []
        self.base_classes: List[str] = []

    def is_derived(self) -> bool:
        """Check if this class derives from any base classes."""
        return len(self.base_classes) > 0
