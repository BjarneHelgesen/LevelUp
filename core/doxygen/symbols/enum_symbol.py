"""
Enum symbol representation.
"""

from typing import List

from .base_symbol import BaseSymbol
from .symbol_kind import SymbolKind


class EnumSymbol(BaseSymbol):
    """
    Represents a C++ enum symbol.

    Attributes:
        enum_values: List of (name, value_string) tuples for enum values
    """

    def __init__(self):
        super().__init__(SymbolKind.ENUM)
        self.enum_values: List[tuple] = []

    def get_value_names(self) -> List[str]:
        """Get list of enum value names."""
        return [name for name, _ in self.enum_values]
