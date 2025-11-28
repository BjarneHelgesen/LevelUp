"""
Doxygen integration for generating function dependency information.
"""

from .doxygen_runner import DoxygenRunner
from .doxygen_parser import DoxygenParser
from .symbol import Symbol, SymbolKind

__all__ = ['DoxygenRunner', 'DoxygenParser', 'Symbol', 'SymbolKind']
