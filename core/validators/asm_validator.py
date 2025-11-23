import re
from abc import ABC

from .base_validator import BaseValidator
from ..compilers.compiled_file import CompiledFile


class BaseASMValidator(BaseValidator, ABC):
    """Base class for ASM validators with shared comparison logic."""

    def __init__(self, compiler):
        self.compiler = compiler
        # Pattern for COMDAT markers (inline functions that linker can discard)
        self.comdat_pattern = re.compile(r'^\s*;\s*COMDAT\s+(\S+)')
        # Pattern for identifiers to canonicalize within function bodies
        self.identifier_pattern = re.compile(
            r'(\?[\w@]+Z\b)|'     # Mangled names (e.g., ?func@@YAHXZ)
            r'(\$LN\d+@\w+)|'     # Local labels (e.g., $LN3@func)
            r'(\$SG\d+)'          # String/data labels (e.g., $SG1234)
        )

    def validate(self, original: CompiledFile, modified: CompiledFile) -> bool:
        # Extract function bodies from both ASMs
        original_funcs = self._extract_functions(original.asm_output)
        modified_funcs = self._extract_functions(modified.asm_output)

        # Get COMDAT functions in modified (these can be added without being in original)
        modified_comdat = self._extract_comdat_function_names(modified.asm_output)

        # For each function in original, find a matching function in modified
        for orig_name, orig_body in original_funcs.items():
            # Skip 'main' - it's the entry point and always present
            match_found = False

            for mod_name, mod_body in modified_funcs.items():
                if self._function_bodies_match(orig_body, mod_body):
                    match_found = True
                    break

            if not match_found:
                return False

        # Check that any extra functions in modified are COMDAT (inline)
        # These are safe to add since linker can discard them
        original_body_set = {self._normalize_body(b) for b in original_funcs.values()}
        for mod_name, mod_body in modified_funcs.items():
            normalized = self._normalize_body(mod_body)
            if normalized not in original_body_set:
                # This function has no match in original - must be COMDAT
                if mod_name not in modified_comdat:
                    return False

        return True

    def _normalize_body(self, body: list) -> tuple:
        """Convert body to comparable tuple, normalizing identifiers within."""
        # Build local identifier map for this function body
        local_map = {}
        func_counter = 0
        label_counter = 0
        data_counter = 0

        normalized = []
        for line in body:
            # Normalize identifiers within the line
            def replace_id(match):
                nonlocal func_counter, label_counter, data_counter
                identifier = match.group(0)
                if identifier not in local_map:
                    if identifier.startswith('?'):
                        local_map[identifier] = f'F{func_counter}'
                        func_counter += 1
                    elif identifier.startswith('$LN'):
                        local_map[identifier] = f'L{label_counter}'
                        label_counter += 1
                    elif identifier.startswith('$SG'):
                        local_map[identifier] = f'D{data_counter}'
                        data_counter += 1
                return local_map.get(identifier, identifier)

            normalized_line = self.identifier_pattern.sub(replace_id, line)
            normalized.append(normalized_line)

        return tuple(normalized)

    def _function_bodies_match(self, body1: list, body2: list) -> bool:
        """Check if two function bodies are functionally equivalent."""
        norm1 = self._normalize_body(body1)
        norm2 = self._normalize_body(body2)
        return norm1 == norm2

    def _extract_comdat_function_names(self, asm_content: str) -> set:
        """Extract raw names of COMDAT functions."""
        if not asm_content:
            return set()

        comdat_functions = set()
        for line in asm_content.splitlines():
            match = self.comdat_pattern.match(line)
            if match:
                comdat_functions.add(match.group(1))
        return comdat_functions

    def _extract_functions(self, asm_content: str) -> dict:
        """Extract function bodies from ASM content.

        Returns dict mapping function name to list of instruction lines.
        """
        if not asm_content:
            return {}

        functions = {}
        current_func = None
        current_body = []

        for line in asm_content.splitlines():
            line = line.rstrip()

            # Strip comments
            if ';' in line:
                line = line.split(';')[0].rstrip()

            # Normalize whitespace
            line = ' '.join(line.split())

            if not line:
                continue

            # Detect function start: "funcname PROC"
            if ' PROC' in line:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == 'PROC':
                    current_func = parts[0]
                    current_body = []
                continue

            # Detect function end: "funcname ENDP"
            if ' ENDP' in line and current_func:
                functions[current_func] = current_body
                current_func = None
                current_body = []
                continue

            # Collect instructions inside function
            if current_func:
                # Skip metadata lines
                if any(line.startswith(p) for p in ['_TEXT', 'pdata', 'xdata', 'CONST', 'DD ', 'DQ ']):
                    continue
                # Skip local variable declarations like "x$ = 8"
                if '$ =' in line:
                    continue
                current_body.append(line)

        return functions


class ASMValidator(BaseASMValidator):
    """ASM validator with configurable optimization level."""

    def __init__(self, compiler, optimization_level: int = 0):
        super().__init__(compiler)
        self._optimization_level = optimization_level

    def get_id(self) -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return f'asm_o{self._optimization_level}'

    def get_name(self) -> str:
        return f"Assembly Comparison (O{self._optimization_level})"

    def get_optimization_level(self) -> int:
        return self._optimization_level
