"""
Parser for Doxygen XML output to extract function dependency information.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Set, Optional
import re

from .. import logger
from .symbol import Symbol, SymbolKind


class FunctionInfo:
    """
    Information about a function extracted from Doxygen XML.

    Attributes:
        name: Function name (without namespace/class prefix)
        qualified_name: Fully qualified name (namespace::class::function)
        file_path: Path to the file where the function is defined
        line_number: Line number of the function definition
        return_type: Return type of the function (unexpanded)
        return_type_expanded: Return type with macros expanded
        parameters: List of (type, name) tuples for parameters (unexpanded)
        parameters_expanded: List of (type, name) tuples with macros expanded
        calls: Set of function IDs this function calls
        called_by: Set of function IDs that call this function
        is_member: True if this is a class member function
        class_name: Name of the class (if member function)
        doxygen_id: Unique Doxygen identifier for this function
    """

    def __init__(self):
        self.name: str = ''
        self.qualified_name: str = ''
        self.file_path: str = ''
        self.line_number: int = 0
        self.return_type: str = ''
        self.return_type_expanded: str = ''
        self.parameters: List[tuple] = []
        self.parameters_expanded: List[tuple] = []
        self.calls: Set[str] = set()
        self.called_by: Set[str] = set()
        self.is_member: bool = False
        self.class_name: str = ''
        self.doxygen_id: str = ''

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

    def __repr__(self) -> str:
        return f"FunctionInfo({self.qualified_name} at {self.file_path}:{self.line_number})"


class DoxygenParser:
    """
    Parses Doxygen XML output to extract function information and dependencies.
    Handles both unexpanded and expanded macro versions.
    """

    def __init__(self, xml_unexpanded_dir: Path, xml_expanded_dir: Path = None):
        """
        Initialize parser with paths to Doxygen XML output directories.

        Args:
            xml_unexpanded_dir: Path to XML directory without macro expansion
            xml_expanded_dir: Optional path to XML directory with macro expansion.
                            If not provided, expanded data won't be available.
        """
        self.xml_unexpanded_dir = Path(xml_unexpanded_dir)
        self.xml_expanded_dir = Path(xml_expanded_dir) if xml_expanded_dir else None
        self._functions: Dict[str, FunctionInfo] = {}
        self._functions_by_name: Dict[str, List[FunctionInfo]] = {}
        self._files: Dict[str, List[FunctionInfo]] = {}
        self._symbols: Dict[str, Symbol] = {}
        self._symbols_by_kind: Dict[str, List[Symbol]] = {}
        self._symbols_by_file: Dict[str, List[Symbol]] = {}
        self._parsed = False

    def parse(self) -> None:
        """Parse all XML files and build function dependency graph."""
        if self._parsed:
            return

        # Parse unexpanded XML first
        index_file = self.xml_unexpanded_dir / 'index.xml'
        if not index_file.exists():
            raise FileNotFoundError(f"Doxygen index.xml not found at {index_file}")

        logger.info(f"Parsing Doxygen XML (unexpanded) from {self.xml_unexpanded_dir}")

        # Parse index to find all compound files
        tree = ET.parse(index_file)
        root = tree.getroot()

        for compound in root.findall('.//compound'):
            refid = compound.get('refid')
            kind = compound.get('kind')

            # We're interested in files and classes for function definitions
            if kind in ('file', 'class', 'struct', 'namespace'):
                compound_file = self.xml_unexpanded_dir / f'{refid}.xml'
                if compound_file.exists():
                    self._parse_compound_file(compound_file, kind, expanded=False)

        # Parse expanded XML if available
        if self.xml_expanded_dir:
            logger.info(f"Parsing Doxygen XML (expanded) from {self.xml_expanded_dir}")
            index_file_expanded = self.xml_expanded_dir / 'index.xml'
            if index_file_expanded.exists():
                tree_expanded = ET.parse(index_file_expanded)
                root_expanded = tree_expanded.getroot()

                for compound in root_expanded.findall('.//compound'):
                    refid = compound.get('refid')
                    kind = compound.get('kind')

                    if kind in ('file', 'class', 'struct', 'namespace'):
                        compound_file = self.xml_expanded_dir / f'{refid}.xml'
                        if compound_file.exists():
                            self._parse_compound_file(compound_file, kind, expanded=True)

        # Build reverse lookup structures
        self._build_indexes()
        self._parsed = True

        logger.info(f"Parsed {len(self._functions)} functions and {len(self._symbols)} symbols from Doxygen XML")

    def _parse_compound_file(self, file_path: Path, compound_kind: str, expanded: bool) -> None:
        """Parse a single compound XML file for function definitions and symbols."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except ET.ParseError as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return

        compounddef = root.find('compounddef')
        if compounddef is None:
            return

        # Get the file location for this compound
        location = compounddef.find('location')
        compound_file = ''
        if location is not None:
            compound_file = location.get('file', '')

        # Get compound name (class/namespace)
        compound_name = ''
        compoundname_elem = compounddef.find('compoundname')
        if compoundname_elem is not None and compoundname_elem.text:
            compound_name = compoundname_elem.text

        # Parse class/struct as Symbol (not for files or namespaces)
        if not expanded and compound_kind in ('class', 'struct'):
            symbol = self._parse_compound_symbol(compounddef, compound_kind)
            if symbol and symbol.doxygen_id:
                self._symbols[symbol.doxygen_id] = symbol

        # Parse all member functions and enums
        for sectiondef in compounddef.findall('.//sectiondef'):
            section_kind = sectiondef.get('kind', '')

            # Function sections we're interested in
            if section_kind in ('func', 'public-func', 'protected-func', 'private-func',
                               'public-static-func', 'protected-static-func', 'private-static-func'):
                for memberdef in sectiondef.findall('memberdef'):
                    if memberdef.get('kind') == 'function':
                        func_info = self._parse_memberdef(memberdef, compound_name, compound_file, expanded)
                        if func_info and func_info.doxygen_id:
                            if expanded:
                                # Merge expanded data into existing function by matching qualified name + file + line
                                # Can't use doxygen_id because it changes between runs due to signature changes
                                match_key = (func_info.qualified_name, func_info.file_path, func_info.line_number)
                                for existing_id, existing_func in self._functions.items():
                                    existing_key = (existing_func.qualified_name, existing_func.file_path, existing_func.line_number)
                                    if match_key == existing_key:
                                        existing_func.return_type_expanded = func_info.return_type
                                        existing_func.parameters_expanded = func_info.parameters
                                        break
                            else:
                                # First pass - create function entry
                                self._functions[func_info.doxygen_id] = func_info

            # Enum sections
            if not expanded and section_kind in ('enum', 'public-type', 'protected-type', 'private-type'):
                for memberdef in sectiondef.findall('memberdef'):
                    if memberdef.get('kind') == 'enum':
                        symbol = self._parse_enum_symbol(memberdef, compound_name, compound_file)
                        if symbol and symbol.doxygen_id:
                            self._symbols[symbol.doxygen_id] = symbol

    def _parse_memberdef(self, memberdef: ET.Element, compound_name: str, default_file: str, expanded: bool) -> Optional[FunctionInfo]:
        """Parse a memberdef element to extract function information."""
        func = FunctionInfo()

        func.doxygen_id = memberdef.get('id', '')

        # Get function name
        name_elem = memberdef.find('name')
        if name_elem is not None and name_elem.text:
            func.name = name_elem.text
        else:
            return None

        # Get qualified name
        qualifiedname_elem = memberdef.find('qualifiedname')
        if qualifiedname_elem is not None and qualifiedname_elem.text:
            func.qualified_name = qualifiedname_elem.text
        else:
            func.qualified_name = f"{compound_name}::{func.name}" if compound_name else func.name

        # Get return type
        type_elem = memberdef.find('type')
        if type_elem is not None:
            func.return_type = self._get_element_text(type_elem)

        # Get parameters
        for param in memberdef.findall('param'):
            param_type = ''
            param_name = ''

            type_elem = param.find('type')
            if type_elem is not None:
                param_type = self._get_element_text(type_elem)

            declname = param.find('declname')
            if declname is not None and declname.text:
                param_name = declname.text

            if param_type:
                func.parameters.append((param_type, param_name))

        # Get file location
        location = memberdef.find('location')
        if location is not None:
            func.file_path = location.get('file', default_file)
            func.line_number = int(location.get('line', 0))
        else:
            func.file_path = default_file

        # Check if member function
        if compound_name:
            func.is_member = True
            func.class_name = compound_name

        # Get function references (calls)
        for ref in memberdef.findall('.//references'):
            refid = ref.get('refid')
            if refid:
                func.calls.add(refid)

        # Get functions that call this one
        for ref in memberdef.findall('.//referencedby'):
            refid = ref.get('refid')
            if refid:
                func.called_by.add(refid)

        return func

    def _get_element_text(self, element: ET.Element) -> str:
        """Extract all text content from an element, including nested refs."""
        parts = []
        if element.text:
            parts.append(element.text)
        for child in element:
            if child.text:
                parts.append(child.text)
            if child.tail:
                parts.append(child.tail)
        return ''.join(parts).strip()

    def _parse_compound_symbol(self, compounddef: ET.Element, compound_kind: str) -> Optional[Symbol]:
        """Parse a compounddef element to extract class/struct symbol."""
        if compound_kind == 'class':
            symbol = Symbol(SymbolKind.CLASS)
        elif compound_kind == 'struct':
            symbol = Symbol(SymbolKind.STRUCT)
        else:
            return None

        symbol.doxygen_id = compounddef.get('id', '')

        compoundname_elem = compounddef.find('compoundname')
        if compoundname_elem is not None and compoundname_elem.text:
            symbol.qualified_name = compoundname_elem.text
            symbol.name = symbol.qualified_name.split('::')[-1]
        else:
            return None

        location = compounddef.find('location')
        if location is not None:
            symbol.file_path = location.get('file', '')
            symbol.line_start = int(location.get('line', 0))
            bodyend = location.get('bodyend')
            if bodyend:
                symbol.line_end = int(bodyend)
            else:
                symbol.line_end = symbol.line_start

        for basecompoundref in compounddef.findall('basecompoundref'):
            if basecompoundref.text:
                symbol.base_classes.append(basecompoundref.text)

        for memberdef in compounddef.findall('.//memberdef'):
            member_id = memberdef.get('id')
            if member_id:
                symbol.members.append(member_id)

        symbol.dependencies = self._extract_dependencies(compounddef)

        return symbol

    def _parse_enum_symbol(self, memberdef: ET.Element, compound_name: str, default_file: str) -> Optional[Symbol]:
        """Parse a memberdef element to extract enum symbol."""
        symbol = Symbol(SymbolKind.ENUM)

        symbol.doxygen_id = memberdef.get('id', '')

        name_elem = memberdef.find('name')
        if name_elem is not None and name_elem.text:
            symbol.name = name_elem.text
        else:
            return None

        qualifiedname_elem = memberdef.find('qualifiedname')
        if qualifiedname_elem is not None and qualifiedname_elem.text:
            symbol.qualified_name = qualifiedname_elem.text
        else:
            symbol.qualified_name = f"{compound_name}::{symbol.name}" if compound_name else symbol.name

        location = memberdef.find('location')
        if location is not None:
            symbol.file_path = location.get('file', default_file)
            symbol.line_start = int(location.get('line', 0))
            bodystart = location.get('bodystart')
            bodyend = location.get('bodyend')
            if bodystart:
                symbol.line_start = int(bodystart)
            if bodyend:
                symbol.line_end = int(bodyend)
            else:
                symbol.line_end = symbol.line_start
        else:
            symbol.file_path = default_file

        for enumvalue in memberdef.findall('enumvalue'):
            name_elem = enumvalue.find('name')
            initializer_elem = enumvalue.find('initializer')
            if name_elem is not None and name_elem.text:
                value_name = name_elem.text
                value_text = ''
                if initializer_elem is not None:
                    value_text = self._get_element_text(initializer_elem)
                symbol.enum_values.append((value_name, value_text))

        return symbol

    def _extract_dependencies(self, element: ET.Element) -> Set[str]:
        """Extract all type dependencies from a symbol."""
        deps = set()

        for type_elem in element.findall('.//type'):
            type_str = self._get_element_text(type_elem)
            deps.update(self._parse_type_references(type_str))

        for ref_elem in element.findall('.//ref'):
            if ref_elem.text:
                deps.add(ref_elem.text)

        return deps

    def _parse_type_references(self, type_str: str) -> Set[str]:
        """Parse a type string to extract referenced type names."""
        refs = set()

        type_str = re.sub(r'\s+', ' ', type_str).strip()
        type_str = re.sub(r'[*&<>,()]', ' ', type_str)

        keywords = {'const', 'volatile', 'static', 'extern', 'inline',
                   'virtual', 'unsigned', 'signed', 'long', 'short',
                   'void', 'int', 'char', 'float', 'double', 'bool'}

        tokens = type_str.split()
        for token in tokens:
            token = token.strip()
            if token and token not in keywords and not token.isdigit():
                refs.add(token)

        return refs

    def _build_indexes(self) -> None:
        """Build lookup indexes after parsing."""
        for func_id, func in self._functions.items():
            # Index by simple name
            if func.name not in self._functions_by_name:
                self._functions_by_name[func.name] = []
            self._functions_by_name[func.name].append(func)

            # Index by file
            if func.file_path:
                if func.file_path not in self._files:
                    self._files[func.file_path] = []
                self._files[func.file_path].append(func)

        for symbol_id, symbol in self._symbols.items():
            if symbol.kind not in self._symbols_by_kind:
                self._symbols_by_kind[symbol.kind] = []
            self._symbols_by_kind[symbol.kind].append(symbol)

            if symbol.file_path:
                if symbol.file_path not in self._symbols_by_file:
                    self._symbols_by_file[symbol.file_path] = []
                self._symbols_by_file[symbol.file_path].append(symbol)

    def get_function_by_id(self, doxygen_id: str) -> Optional[FunctionInfo]:
        """Get a function by its Doxygen ID."""
        self.parse()
        return self._functions.get(doxygen_id)

    def get_functions_by_name(self, name: str) -> List[FunctionInfo]:
        """
        Get all functions matching a name.

        Args:
            name: Simple function name (without namespace/class prefix)

        Returns:
            List of FunctionInfo objects matching the name
        """
        self.parse()
        return self._functions_by_name.get(name, [])

    def get_functions_in_file(self, file_path: str) -> List[FunctionInfo]:
        """
        Get all functions defined in a file.

        Args:
            file_path: Path to the source file (as recorded by Doxygen)

        Returns:
            List of FunctionInfo objects in the file
        """
        self.parse()

        # Try exact match first
        if file_path in self._files:
            return self._files[file_path]

        # Try normalized path matching
        normalized = Path(file_path).name
        for recorded_path, functions in self._files.items():
            if Path(recorded_path).name == normalized:
                return functions

        return []

    def get_callers(self, func: FunctionInfo) -> List[FunctionInfo]:
        """Get all functions that call the given function."""
        self.parse()
        return [self._functions[fid] for fid in func.called_by if fid in self._functions]

    def get_callees(self, func: FunctionInfo) -> List[FunctionInfo]:
        """Get all functions called by the given function."""
        self.parse()
        return [self._functions[fid] for fid in func.calls if fid in self._functions]

    def get_all_functions(self) -> List[FunctionInfo]:
        """Get all parsed functions."""
        self.parse()
        return list(self._functions.values())

    def get_all_files(self) -> List[str]:
        """Get list of all files with functions."""
        self.parse()
        return list(self._files.keys())

    def find_function(self, qualified_name: str) -> Optional[FunctionInfo]:
        """
        Find a function by its qualified name.

        Args:
            qualified_name: Fully qualified name like "namespace::class::function"

        Returns:
            FunctionInfo if found, None otherwise
        """
        self.parse()
        for func in self._functions.values():
            if func.qualified_name == qualified_name:
                return func
        return None

    def get_call_graph(self, func: FunctionInfo, depth: int = 3) -> Dict[str, Set[str]]:
        """
        Get the call graph starting from a function up to a certain depth.

        Args:
            func: Starting function
            depth: Maximum depth to traverse

        Returns:
            Dict mapping function qualified names to sets of called function names
        """
        self.parse()
        graph = {}
        visited = set()

        def traverse(f: FunctionInfo, current_depth: int):
            if current_depth > depth or f.doxygen_id in visited:
                return
            visited.add(f.doxygen_id)

            callees = self.get_callees(f)
            graph[f.qualified_name] = {c.qualified_name for c in callees}

            for callee in callees:
                traverse(callee, current_depth + 1)

        traverse(func, 0)
        return graph

    def get_all_symbols(self) -> List[Symbol]:
        """Get all parsed symbols."""
        self.parse()
        return list(self._symbols.values())

    def get_symbols_by_kind(self, kind: str) -> List[Symbol]:
        """Get all symbols of a specific kind."""
        self.parse()
        return self._symbols_by_kind.get(kind, [])

    def get_symbols_in_file(self, file_path: str) -> List[Symbol]:
        """Get all symbols in a specific file."""
        self.parse()

        if file_path in self._symbols_by_file:
            return self._symbols_by_file[file_path]

        normalized = Path(file_path).name
        for recorded_path, symbols in self._symbols_by_file.items():
            if Path(recorded_path).name == normalized:
                return symbols

        return []

    def get_symbol_by_id(self, doxygen_id: str) -> Optional[Symbol]:
        """Get a symbol by its Doxygen ID."""
        self.parse()
        return self._symbols.get(doxygen_id)

    def find_symbol(self, qualified_name: str) -> Optional[Symbol]:
        """Find a symbol by its qualified name."""
        self.parse()
        for symbol in self._symbols.values():
            if symbol.qualified_name == qualified_name:
                return symbol
        return None

    def get_symbols_at_line(self, file_path: str, line: int) -> List[Symbol]:
        """Get all symbols that contain a specific line."""
        symbols = self.get_symbols_in_file(file_path)
        return [s for s in symbols if s.line_start <= line <= s.line_end]
