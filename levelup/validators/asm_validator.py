import difflib
import re
from pathlib import Path

from .base_validator import BaseValidator


class ASMValidator(BaseValidator):
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

    @staticmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return 'asm'

    @staticmethod
    def get_name() -> str:
        return "Assembly Comparison"

    def validate(self, original_asm_path, modified_asm_path):
        original_lines = self._normalize_asm_file(original_asm_path)
        modified_lines = self._normalize_asm_file(modified_asm_path)

        if original_lines == modified_lines:
            return True

        return self._check_acceptable_differences(original_lines, modified_lines)

    def _normalize_asm_file(self, asm_path):
        if not Path(asm_path).exists():
            raise FileNotFoundError(f"ASM file not found: {asm_path}")
        
        with open(asm_path, 'r', errors='ignore') as f:
            lines = f.readlines()
        
        normalized = []
        in_function = False
        
        for line in lines:
            line = line.rstrip()
            
            # Skip lines matching ignore patterns
            if any(pattern.match(line) for pattern in self.ignore_patterns):
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
        for line in inserted_lines:
            if 'nop' in line.lower() or 'align' in line.lower():
                continue
            return False
        return True

    def get_diff_report(self, original_asm_path, modified_asm_path):
        original_lines = self._normalize_asm_file(original_asm_path)
        modified_lines = self._normalize_asm_file(modified_asm_path)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=str(original_asm_path),
            tofile=str(modified_asm_path),
            lineterm=''
        )
        
        return '\n'.join(diff)
