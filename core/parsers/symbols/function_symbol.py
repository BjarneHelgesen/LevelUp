"""
Function symbol representation.
"""

from typing import List, Set

from .base_symbol import BaseSymbol
from .symbol_kind import SymbolKind


class FunctionSymbol(BaseSymbol):
    """
    Represents a C++ function symbol.

    Attributes:
        return_type: Return type of the function (unexpanded)
        return_type_expanded: Return type with macros expanded
        parameters: List of (type, name) tuples for parameters (unexpanded)
        parameters_expanded: List of (type, name) tuples with macros expanded
        calls: Set of Doxygen IDs this function calls
        called_by: Set of Doxygen IDs that call this function
        is_member: True if this is a class member function
        class_name: Name of the class (if member function)
    """

    def __init__(self):
        super().__init__(SymbolKind.FUNCTION)
        self.return_type: str = ''
        self.return_type_expanded: str = ''
        self.parameters: List[tuple] = []
        self.parameters_expanded: List[tuple] = []
        self.calls: Set[str] = set()
        self.called_by: Set[str] = set()
        self.is_member: bool = False
        self.class_name: str = ''

    def get_signature(self, expanded: bool = False) -> str:
        """
        Return the function signature as a string.

        Args:
            expanded: If True, return signature with expanded macros
        """
        params = self.parameters_expanded if expanded else self.parameters
        ret_type = self.return_type_expanded if expanded else self.return_type
        params_str = ', '.join(f'{ptype} {pname}' for ptype, pname in params)
        return f'{ret_type} {self.qualified_name}({params_str})'
