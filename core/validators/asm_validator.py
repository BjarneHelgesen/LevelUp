import difflib
import re
from abc import ABC

from .base_validator import BaseValidator
from ..compilers.compiled_file import CompiledFile


class BaseASMValidator(BaseValidator, ABC):
    """Base class for ASM validators with shared comparison logic."""

    def __init__(self, compiler):
        self.compiler = compiler
        self.ignore_patterns = [
            re.compile(r'^\s*;.*$'),
            re.compile(r'^\s*TITLE\s+.*$'),
            re.compile(r'^\s*\.file\s+.*$'),
            re.compile(r'^\s*\.ident\s+.*$'),
            re.compile(r'^\s*include\s+.*$'),
            re.compile(r'^\s*INCLUDELIB\s+.*$'),
            re.compile(r'^\s*\.model\s+.*$'),
            re.compile(r'^\s*PUBLIC\s+.*$'),
            re.compile(r'^\s*EXTRN\s+.*$'),
            re.compile(r'^\s*\?\?\d+.*$'),
            re.compile(r'^\s*\$.*$'),
            re.compile(r'^\s*DD\s+__real@.*$'),
            re.compile(r'^\s*DD\s+__mask@.*$'),
        ]
        # Pattern for COMDAT markers - tracked separately to identify inline functions
        # MSVC format: ";	COMDAT ?funcname@@..."
        self.comdat_pattern = re.compile(r'^\s*;\s*COMDAT\s+(\S+)')

        # Patterns for identifiers to canonicalize
        # MSVC mangled names: ?name@@...@Z
        self.mangled_name_pattern = re.compile(r'\?[\w@]+@Z')
        # Local labels: $LN3@func, $LN10@len
        self.local_label_pattern = re.compile(r'\$LN\d+@\w+')
        # String/data labels: $SG1234
        self.data_label_pattern = re.compile(r'\$SG\d+')
        # Combined pattern for all identifiers
        self.identifier_pattern = re.compile(
            r'(\?[\w@]+@Z)|'      # Mangled names
            r'(\$LN\d+@\w+)|'     # Local labels
            r'(\$SG\d+)'          # String/data labels
        )

    def validate(self, original: CompiledFile, modified: CompiledFile) -> bool:
        original_lines = self._normalize_asm(original.asm_output)
        modified_lines = self._normalize_asm(modified.asm_output)

        # Track canonical COMDAT function names in modified ASM
        modified_id_map = self._build_identifier_map(modified.asm_output)
        self._modified_comdat_functions = self._extract_comdat_functions(
            modified.asm_output, modified_id_map
        )

        if original_lines == modified_lines:
            return True

        return self._check_acceptable_differences(original_lines, modified_lines)

    def _extract_comdat_functions(self, asm_content: str, identifier_map: dict) -> set:
        """Extract canonical names of COMDAT functions (inline functions linker can discard)."""
        if not asm_content:
            return set()

        comdat_functions = set()
        for line in asm_content.splitlines():
            match = self.comdat_pattern.match(line)
            if match:
                # Extract function name and convert to canonical name
                func_name = match.group(1)
                canonical_name = identifier_map.get(func_name, func_name)
                comdat_functions.add(canonical_name)

        return comdat_functions

    def _build_identifier_map(self, asm_content: str) -> dict:
        """Build a mapping of identifiers to canonical names based on order of appearance."""
        if not asm_content:
            return {}

        identifier_map = {}
        func_counter = 0
        label_counter = 0
        data_counter = 0

        for match in self.identifier_pattern.finditer(asm_content):
            identifier = match.group(0)
            if identifier in identifier_map:
                continue

            # Assign canonical name based on type
            if identifier.startswith('?'):
                identifier_map[identifier] = f'FUNC_{func_counter}'
                func_counter += 1
            elif identifier.startswith('$LN'):
                identifier_map[identifier] = f'LABEL_{label_counter}'
                label_counter += 1
            elif identifier.startswith('$SG'):
                identifier_map[identifier] = f'DATA_{data_counter}'
                data_counter += 1

        return identifier_map

    def _canonicalize_line(self, line: str, identifier_map: dict) -> str:
        """Replace all identifiers in a line with their canonical names."""
        def replace_identifier(match):
            identifier = match.group(0)
            return identifier_map.get(identifier, identifier)
        return self.identifier_pattern.sub(replace_identifier, line)

    def _normalize_asm(self, asm_content: str):
        if not asm_content:
            return []

        # Build identifier map for this ASM content
        identifier_map = self._build_identifier_map(asm_content)

        lines = asm_content.splitlines()

        normalized = []
        in_function = False

        for line in lines:
            line = line.rstrip()

            # Strip inline comments (everything after semicolon)
            if ';' in line:
                line = line.split(';')[0].rstrip()

            # Skip lines matching ignore patterns
            if any(pattern.match(line) for pattern in self.ignore_patterns):
                continue

            # Skip COMDAT markers (tracked separately)
            if self.comdat_pattern.match(line):
                continue

            # Skip empty lines outside of functions
            if not line and not in_function:
                continue

            # Track when we're inside a function
            if line.startswith('_TEXT') or line.startswith('.text'):
                in_function = True
            elif line.startswith('_TEXT ENDS') or line.startswith('.text ENDS'):
                in_function = False

            # Normalize whitespace
            line = ' '.join(line.split())

            # Canonicalize all identifiers (function names, labels, data refs)
            line = self._canonicalize_line(line, identifier_map)

            if line:
                normalized.append(line)

        return normalized

    def _check_acceptable_differences(self, original_lines, modified_lines):
        differ = difflib.SequenceMatcher(None, original_lines, modified_lines)

        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag == 'equal':
                continue

            # Check if this is an acceptable difference
            if tag == 'replace':
                original_block = original_lines[i1:i2]
                modified_block = modified_lines[j1:j2]

                if not self._is_acceptable_replacement(original_block, modified_block):
                    return False

            elif tag in ('delete', 'insert'):
                # Deletions and insertions need careful checking
                if tag == 'delete':
                    deleted = original_lines[i1:i2]
                    if not self._is_safe_to_delete(deleted):
                        return False
                else:  # insert
                    inserted = modified_lines[j1:j2]
                    if not self._is_safe_to_insert(inserted):
                        return False

        return True

    def _is_acceptable_replacement(self, original_block, modified_block):
        if len(original_block) == len(modified_block):
            for orig, mod in zip(original_block, modified_block):
                # Check for register substitution
                if self._is_register_substitution(orig, mod):
                    continue

                # Check for equivalent operations
                if self._are_equivalent_operations(orig, mod):
                    continue

                # If we can't determine equivalence, be conservative
                return False

        # Check for instruction reordering
        if set(original_block) == set(modified_block):
            # Same instructions, just reordered - need to check dependencies
            return self._check_reordering_safety(original_block, modified_block)

        return False

    def _is_register_substitution(self, orig_line, mod_line):
        reg_pattern = re.compile(r'\b(eax|ebx|ecx|edx|esi|edi|ebp|esp|'
                                 r'rax|rbx|rcx|rdx|rsi|rdi|rbp|rsp|'
                                 r'ax|bx|cx|dx|si|di|bp|sp|'
                                 r'al|bl|cl|dl|ah|bh|ch|dh)\b', re.IGNORECASE)

        orig_normalized = reg_pattern.sub('REG', orig_line)
        mod_normalized = reg_pattern.sub('REG', mod_line)

        return orig_normalized == mod_normalized

    def _are_equivalent_operations(self, orig_line, mod_line):
        if 'lea' in orig_line and 'mov' in mod_line:
            return True

        if 'add' in orig_line and 'lea' in mod_line:
            return True

        return False

    def _check_reordering_safety(self, original_block, modified_block):
        if len(original_block) <= 3:
            return True

        return False

    def _is_safe_to_delete(self, deleted_lines):
        for line in deleted_lines:
            if any(op in line.lower() for op in ['mov', 'add', 'sub', 'call', 'jmp', 'ret']):
                return False
        return True

    def _is_safe_to_insert(self, inserted_lines):
        # Check if inserted lines form a complete COMDAT function (inline function)
        # These are safe to add since the linker can discard them if unused
        if self._is_comdat_function_block(inserted_lines):
            return True

        for line in inserted_lines:
            if 'nop' in line.lower() or 'align' in line.lower():
                continue
            return False
        return True

    def _is_comdat_function_block(self, lines):
        """Check if lines represent a complete COMDAT function block.

        Lines are already canonicalized, so we check for canonical FUNC_N names.
        """
        if not hasattr(self, '_modified_comdat_functions'):
            return False

        # Look for PROC declaration that matches a known COMDAT function
        for line in lines:
            if ' PROC' in line:
                func_name = line.split()[0]
                # func_name is now canonical (e.g., FUNC_0)
                if func_name in self._modified_comdat_functions:
                    # Verify the block is complete (has matching ENDP)
                    has_endp = any(func_name in l and ' ENDP' in l for l in lines)
                    if has_endp:
                        return True
        return False


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
