"""
Symbol hierarchy for C++ code entities.

This package provides a type-safe abstraction for symbols extracted from source parsing,
designed to support multiple parser backends (Doxygen, Clang AST, etc.).
"""

from .symbol_kind import SymbolKind
from .base_symbol import BaseSymbol
from .function_symbol import FunctionSymbol
from .class_symbol import ClassSymbol
from .enum_symbol import EnumSymbol
from .symbol_factory import SymbolFactory

__all__ = [
    'SymbolKind',
    'BaseSymbol',
    'FunctionSymbol',
    'ClassSymbol',
    'EnumSymbol',
    'SymbolFactory',
]
