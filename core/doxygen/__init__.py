"""
Doxygen integration for generating function dependency information.
"""

from .doxygen_runner import DoxygenRunner
from .doxygen_parser import DoxygenParser, FunctionInfo
from .symbol import Symbol, SymbolKind

__all__ = ['DoxygenRunner', 'DoxygenParser', 'FunctionInfo', 'Symbol', 'SymbolKind']
