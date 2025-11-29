"""
Symbol kind enumeration for type-safe symbol classification.
"""

from enum import Enum


class SymbolKind(Enum):
    """Type-safe enumeration of C++ symbol kinds."""
    FUNCTION = "function"
    CLASS = "class"
    STRUCT = "struct"
    ENUM = "enum"
    TYPEDEF = "typedef"
    VARIABLE = "variable"
    NAMESPACE = "namespace"
