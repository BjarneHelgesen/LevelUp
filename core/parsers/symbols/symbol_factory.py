"""
Factory for creating appropriate symbol subclass instances.
"""

from .symbol_kind import SymbolKind
from .base_symbol import BaseSymbol
from .function_symbol import FunctionSymbol
from .class_symbol import ClassSymbol
from .enum_symbol import EnumSymbol


class SymbolFactory:
    """
    Factory for instantiating appropriate symbol subclass based on kind.

    Ensures parser implementation can be replaced without changing consuming code.
    """

    @staticmethod
    def create(kind: SymbolKind) -> BaseSymbol:
        """
        Create appropriate symbol subclass instance based on kind.

        Args:
            kind: SymbolKind enum value

        Returns:
            Instance of appropriate BaseSymbol subclass

        Raises:
            ValueError: If kind is not supported
        """
        if kind == SymbolKind.FUNCTION:
            return FunctionSymbol()
        elif kind in (SymbolKind.CLASS, SymbolKind.STRUCT):
            return ClassSymbol(kind)
        elif kind == SymbolKind.ENUM:
            return EnumSymbol()
        else:
            raise ValueError(f"Unsupported symbol kind: {kind}")

    @staticmethod
    def create_from_string(kind_str: str) -> BaseSymbol:
        """
        Create symbol from string kind (for backward compatibility).

        Args:
            kind_str: String representation of symbol kind

        Returns:
            Instance of appropriate BaseSymbol subclass
        """
        kind = SymbolKind(kind_str)
        return SymbolFactory.create(kind)
