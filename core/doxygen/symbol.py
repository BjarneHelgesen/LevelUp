"""
Symbol class for representing C++ code entities from Doxygen XML.
"""

from typing import Set, List, Optional, Dict


class SymbolKind:
    FUNCTION = "function"
    CLASS = "class"
    STRUCT = "struct"
    ENUM = "enum"
    TYPEDEF = "typedef"
    VARIABLE = "variable"
    NAMESPACE = "namespace"


class Symbol:
    """
    Represents a C++ symbol (function, class, enum, etc.) extracted from Doxygen XML.
    """

    def __init__(self, kind: str):
        self.kind: str = kind
        self.name: str = ''
        self.qualified_name: str = ''
        self.file_path: str = ''
        self.line_start: int = 0
        self.line_end: int = 0
        self.prototype: str = ''
        self.parsed_prototype: Optional[Dict] = None
        self.dependencies: Set[str] = set()
        self.doxygen_id: str = ''

        self.return_type: str = ''
        self.return_type_expanded: str = ''
        self.parameters: List[tuple] = []
        self.parameters_expanded: List[tuple] = []
        self.calls: Set[str] = set()
        self.called_by: Set[str] = set()
        self.is_member: bool = False
        self.class_name: str = ''

        self.members: List[str] = []
        self.base_classes: List[str] = []

        self.enum_values: List[tuple] = []

    def get_signature(self, expanded: bool = False) -> str:
        """
        Return the function signature as a string (for functions).
        """
        if self.kind != SymbolKind.FUNCTION:
            return self.prototype

        params = self.parameters_expanded if expanded else self.parameters
        ret_type = self.return_type_expanded if expanded else self.return_type
        params_str = ', '.join(f'{ptype} {pname}' for ptype, pname in params)
        return f'{ret_type} {self.qualified_name}({params_str})'

    def __repr__(self) -> str:
        return f"Symbol({self.kind}: {self.qualified_name} at {self.file_path}:{self.line_start}-{self.line_end})"
