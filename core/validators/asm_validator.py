import re
from abc import ABC

from .base_validator import BaseValidator
from ..compilers.compiled_file import CompiledFile
from ..compilers.compiler_type import CompilerType


class BaseASMValidator(BaseValidator, ABC):
    """Base class for ASM validators with shared comparison logic."""

    def __init__(self):
        # Pattern for COMDAT markers (inline functions that linker can discard)
        self.comdat_pattern = re.compile(r'^\s*;\s*COMDAT\s+(\S+)')
        # Pattern for identifiers to canonicalize within function bodies
        self.identifier_pattern = re.compile(
            r'(\?[\w@]+Z\b)|'     # Mangled names (e.g., ?func@@YAHXZ)
            r'(\$LN\d+@\w+)|'     # Local labels with function (e.g., $LN3@func)
            r'(\$LN\d+:?)|'       # Standalone local labels (e.g., $LN6, $LN6:)
            r'(\$SG\d+)|'         # String/data labels (e.g., $SG1234)
            r'(\.LBB\d+_\d+)|'    # Clang basic block labels (e.g., .LBB0_1, .LBB1_3)
            r'(\.Ltmp\d+)|'       # Clang temp labels (e.g., .Ltmp0)
            r'(\.L[A-Z]+\d+)'     # Other Clang labels (e.g., .LCPI0_0)
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
                    elif identifier.startswith('$LN') or identifier.startswith('.LBB') or identifier.startswith('.Ltmp'):
                        local_map[identifier] = f'L{label_counter}'
                        label_counter += 1
                    elif identifier.startswith('$SG') or identifier.startswith('.L'):
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

    def _detect_asm_format(self, asm_content: str) -> CompilerType | str:
        """Detect whether assembly is MSVC or Clang format.

        Returns CompilerType enum or 'unknown' string.
        """
        if not asm_content:
            return 'unknown'

        # MSVC uses PROC/ENDP markers
        if ' PROC' in asm_content and ' ENDP' in asm_content:
            return CompilerType.MSVC

        # Clang uses .globl directives and label-based functions
        if '.globl' in asm_content or '.text' in asm_content:
            return CompilerType.CLANG

        return 'unknown'

    def _extract_functions(self, asm_content: str) -> dict:
        """Extract function bodies from ASM content.

        Returns dict mapping function name to list of instruction lines.
        Automatically detects MSVC or Clang assembly format.
        """
        if not asm_content:
            return {}

        format_type = self._detect_asm_format(asm_content)

        if format_type == CompilerType.MSVC:
            return self._extract_functions_msvc(asm_content)
        elif format_type == CompilerType.CLANG:
            return self._extract_functions_clang(asm_content)
        else:
            return {}

    def _extract_functions_msvc(self, asm_content: str) -> dict:
        """Extract function bodies from MSVC assembly format.

        Returns dict mapping function name to list of instruction lines.
        """
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

    def _extract_functions_clang(self, asm_content: str) -> dict:
        """Extract function bodies from Clang/LLVM assembly format.

        Returns dict mapping function name to list of instruction lines.
        """
        functions = {}
        current_func = None
        current_body = []
        in_debug_section = False
        in_text_section = True  # Start assuming we're in .text (code) section

        for line in asm_content.splitlines():
            line = line.rstrip()

            # Track section changes
            if line.strip().startswith('.section'):
                # Save current function before changing sections
                if current_func and current_body:
                    functions[current_func] = current_body
                current_func = None
                current_body = []

                # Check if this is a code section (.text) or data section (.bss, .data, etc.)
                if 'debug' in line.lower():
                    in_debug_section = True
                    in_text_section = False
                elif '.text' in line:
                    in_debug_section = False
                    in_text_section = True
                else:
                    # Other sections (.bss, .data, .rodata, etc.) are not code
                    in_debug_section = False
                    in_text_section = False
                continue

            # .text directive puts us back in code section
            if line.strip() == '.text':
                in_text_section = True
                in_debug_section = False
                if current_func and current_body:
                    functions[current_func] = current_body
                current_func = None
                current_body = []
                continue

            # Skip debug sections entirely
            if in_debug_section:
                continue

            # Skip non-code sections
            if not in_text_section:
                continue

            # Strip comments (Clang uses # for comments)
            if '#' in line:
                # Keep line, just remove comment part
                line = line.split('#')[0].rstrip()

            # Normalize whitespace
            line = ' '.join(line.split())

            if not line:
                continue

            # Detect function end/start markers
            if line.startswith('.globl') or line.startswith('.addrsig'):
                # Save current function and reset
                if current_func and current_body:
                    functions[current_func] = current_body
                current_func = None
                current_body = []
                continue

            # Detect function start: label followed by colon (e.g., "main:" or "\"?add@@YAHHH@Z\":")
            # Function names can be quoted for mangled names
            if line.endswith(':') and not line.startswith('.'):
                # Extract function name (remove colon and quotes)
                func_name = line[:-1].strip().strip('"')
                # Skip internal labels that start with .L
                if not func_name.startswith('.L') and not func_name.startswith('.seh'):
                    current_func = func_name
                    current_body = []
                continue

            # Collect actual instructions within functions
            if current_func:

                # Skip assembler directives and metadata
                if any(line.startswith(p) for p in ['.seh_', '.def', '.scl', '.type', '.endef',
                                                     '.p2align', '.file', '.intel_syntax',
                                                     '@feat.00', '.L', '.cfi_']):
                    continue

                # Collect actual instructions
                current_body.append(line)

        # Save last function if any
        if current_func and current_body:
            functions[current_func] = current_body

        return functions


class ASMValidatorO0(BaseASMValidator):
    """ASM validator using no optimization (/Od)."""

    @staticmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return 'asm_o0'

    @staticmethod
    def get_name() -> str:
        return "Assembly Comparison (O0)"

    @staticmethod
    def get_optimization_level() -> int:
        return 0


class ASMValidatorO3(BaseASMValidator):
    """ASM validator using maximum optimization (/Ox)."""

    @staticmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return 'asm_o3'

    @staticmethod
    def get_name() -> str:
        return "Assembly Comparison (O3)"

    @staticmethod
    def get_optimization_level() -> int:
        return 3
