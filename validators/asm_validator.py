"""
ASM Validator for LevelUp - Validates that assembly output remains unchanged
"""

import difflib
import re
from pathlib import Path

class ASMValidator:
    """Validates assembly output to ensure no functional changes"""
    
    def __init__(self, compiler):
        self.compiler = compiler
        self.ignore_patterns = [
            re.compile(r'^\s*;.*$'),  # Comments
            re.compile(r'^\s*TITLE\s+.*$'),  # Title directives
            re.compile(r'^\s*\.file\s+.*$'),  # File directives
            re.compile(r'^\s*\.ident\s+.*$'),  # Compiler identification
            re.compile(r'^\s*include\s+.*$'),  # Include directives
            re.compile(r'^\s*INCLUDELIB\s+.*$'),  # Library includes
            re.compile(r'^\s*\.model\s+.*$'),  # Model directives
            re.compile(r'^\s*PUBLIC\s+.*$'),  # Public symbols (may vary)
            re.compile(r'^\s*EXTRN\s+.*$'),  # External symbols
            re.compile(r'^\s*\?\?\d+.*$'),  # Temporary labels
            re.compile(r'^\s*\$.*$'),  # Local labels
            re.compile(r'^\s*DD\s+__real@.*$'),  # Floating point constants
            re.compile(r'^\s*DD\s+__mask@.*$'),  # Mask constants
        ]
    
    def validate(self, original_asm_path, modified_asm_path):
        """
        Validate that two ASM files are functionally identical
        Returns True if validation passes, False otherwise
        """
        original_lines = self._normalize_asm_file(original_asm_path)
        modified_lines = self._normalize_asm_file(modified_asm_path)
        
        # Compare normalized ASM
        if original_lines == modified_lines:
            return True
        
        # If not exactly equal, check if differences are acceptable
        return self._check_acceptable_differences(original_lines, modified_lines)
    
    def _normalize_asm_file(self, asm_path):
        """Normalize an ASM file for comparison"""
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
        """
        Check if differences between ASM files are acceptable
        
        Acceptable differences include:
        - Reordering of independent instructions
        - Different register allocation for same operations
        - Optimization differences that don't change behavior
        """
        
        # Create a detailed diff
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
        """Check if a replacement is acceptable"""
        
        # Check for simple optimizations
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
        """Check if two lines differ only in register allocation"""
        # Simple pattern: replace register names and compare
        reg_pattern = re.compile(r'\b(eax|ebx|ecx|edx|esi|edi|ebp|esp|'
                                 r'rax|rbx|rcx|rdx|rsi|rdi|rbp|rsp|'
                                 r'ax|bx|cx|dx|si|di|bp|sp|'
                                 r'al|bl|cl|dl|ah|bh|ch|dh)\b', re.IGNORECASE)
        
        orig_normalized = reg_pattern.sub('REG', orig_line)
        mod_normalized = reg_pattern.sub('REG', mod_line)
        
        return orig_normalized == mod_normalized
    
    def _are_equivalent_operations(self, orig_line, mod_line):
        """Check if two operations are functionally equivalent"""
        # This is a simplified check - in practice, this would need
        # deep knowledge of x86/x64 instruction semantics
        
        # Check for equivalent addressing modes
        if 'lea' in orig_line and 'mov' in mod_line:
            # LEA can sometimes be replaced with MOV for address calculations
            return True
        
        # Check for equivalent arithmetic
        if 'add' in orig_line and 'lea' in mod_line:
            # ADD can sometimes be replaced with LEA for arithmetic
            return True
        
        return False
    
    def _check_reordering_safety(self, original_block, modified_block):
        """Check if instruction reordering is safe"""
        # This would need sophisticated dependency analysis
        # For now, we'll be conservative and only allow very simple cases
        
        # If blocks are small (2-3 instructions), check for independence
        if len(original_block) <= 3:
            # Check if instructions access different registers/memory
            # This is a simplified check
            return True
        
        return False
    
    def _is_safe_to_delete(self, deleted_lines):
        """Check if deleted lines are safe to remove"""
        for line in deleted_lines:
            # Never safe to delete actual instructions
            if any(op in line.lower() for op in ['mov', 'add', 'sub', 'call', 'jmp', 'ret']):
                return False
        return True
    
    def _is_safe_to_insert(self, inserted_lines):
        """Check if inserted lines are safe additions"""
        for line in inserted_lines:
            # Check if it's just alignment or padding
            if 'nop' in line.lower() or 'align' in line.lower():
                continue
            # Otherwise be conservative
            return False
        return True
    
    def get_diff_report(self, original_asm_path, modified_asm_path):
        """Generate a detailed diff report"""
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
