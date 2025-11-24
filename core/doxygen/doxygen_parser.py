"""
Parser for Doxygen XML output to extract function dependency information.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Set, Optional

from .. import logger


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

        logger.info(f"Parsed {len(self._functions)} functions from Doxygen XML")

    def _parse_compound_file(self, file_path: Path, compound_kind: str, expanded: bool) -> None:
        """Parse a single compound XML file for function definitions."""
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

        # Parse all member functions
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
