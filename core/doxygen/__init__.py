"""
Doxygen integration for generating function dependency information.
"""

from .doxygen_runner import DoxygenRunner
from .doxygen_parser import DoxygenParser, FunctionInfo

__all__ = ['DoxygenRunner', 'DoxygenParser', 'FunctionInfo']
