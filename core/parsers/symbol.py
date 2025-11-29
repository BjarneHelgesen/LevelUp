"""
Backward compatibility shim for old Symbol imports.

DEPRECATED: Import from core.parsers.symbols instead.
"""

from .symbols import (
    SymbolKind as _SymbolKind,
    BaseSymbol,
    FunctionSymbol,
    ClassSymbol,
    EnumSymbol,
    SymbolFactory
)


class SymbolKind:
    """
    DEPRECATED: Use symbols.SymbolKind enum instead.
    Kept for backward compatibility.
    """
    FUNCTION = "function"
    CLASS = "class"
    STRUCT = "struct"
    ENUM = "enum"
    TYPEDEF = "typedef"
    VARIABLE = "variable"
    NAMESPACE = "namespace"


class Symbol(BaseSymbol):
    """
    DEPRECATED: Use specialized symbol classes (FunctionSymbol, ClassSymbol, etc.) instead.

    Legacy monolithic symbol class maintained for backward compatibility.
    New code should use the specialized symbol hierarchy from core.parsers.symbols.
    """

    def __init__(self, kind):
        if isinstance(kind, str):
            kind_enum = _SymbolKind(kind)
        else:
            kind_enum = kind

        super().__init__(kind_enum)

        self.return_type: str = ''
        self.return_type_expanded: str = ''
        self.parameters: list = []
        self.parameters_expanded: list = []
        self.calls: set = set()
        self.called_by: set = set()
        self.is_member: bool = False
        self.class_name: str = ''

        self.members: list = []
        self.base_classes: list = []

        self.enum_values: list = []

    def get_signature(self, expanded: bool = False) -> str:
        """
        Return the function signature as a string (for functions).
        """
        if self.kind != _SymbolKind.FUNCTION:
            return self.prototype

        params = self.parameters_expanded if expanded else self.parameters
        ret_type = self.return_type_expanded if expanded else self.return_type
        params_str = ', '.join(f'{ptype} {pname}' for ptype, pname in params)
        return f'{ret_type} {self.qualified_name}({params_str})'
