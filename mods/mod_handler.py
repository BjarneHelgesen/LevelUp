"""
Mod Handler for LevelUp - Manages and applies modifications to C++ code
"""

import re
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from .base_mod import BaseMod
from .mod_factory import ModFactory


class ModHandler:
    """Handles application of mods to C++ code"""

    def __init__(self):
        self.mod_history = []
        self.mod_factory = ModFactory()

    def apply_mod(self, cpp_file, mod_data):
        """
        Apply a mod to a C++ file
        Returns path to modified file
        """
        mod_type = mod_data.get('mod_type', 'custom')

        # Create the mod instance using the factory
        try:
            mod_instance = self.mod_factory.create_mod(mod_type)
        except (ValueError, NotImplementedError) as e:
            raise ValueError(f"Cannot create mod: {e}")

        # Validate before applying
        is_valid, message = mod_instance.validate_before_apply(Path(cpp_file))
        if not is_valid:
            raise ValueError(f"Mod validation failed: {message}")

        # Apply the mod
        modified_file = mod_instance.apply(Path(cpp_file))

        # Record in history
        self.mod_history.append({
            'file': str(cpp_file),
            'mod_type': mod_type,
            'timestamp': datetime.now().isoformat(),
            'mod_data': mod_data,
            'mod_metadata': mod_instance.get_metadata()
        })

        return modified_file
    
    def _remove_inline(self, cpp_file, mod_data):
        """Remove inline keywords from functions"""
        with open(cpp_file, 'r') as f:
            content = f.read()
        
        # Pattern to match inline keyword
        pattern = r'\binline\s+'
        content = re.sub(pattern, '', content)
        
        with open(cpp_file, 'w') as f:
            f.write(content)
    
    def _add_const(self, cpp_file, mod_data):
        """Add const correctness where appropriate"""
        with open(cpp_file, 'r') as f:
            lines = f.readlines()
        
        modified_lines = []
        for line in lines:
            # Add const to member functions that don't modify state
            if re.match(r'^\s*\w+.*\(.*\)\s*{', line):
                # Check if it's a getter or similar
                if any(keyword in line for keyword in ['get', 'Get', 'is', 'Is', 'has', 'Has']):
                    if ' const' not in line and ';' not in line:
                        line = re.sub(r'\)', ') const', line, count=1)
            
            modified_lines.append(line)
        
        with open(cpp_file, 'w') as f:
            f.writelines(modified_lines)
    
    def _modernize_for_loops(self, cpp_file, mod_data):
        """Convert traditional for loops to range-based for loops where possible"""
        with open(cpp_file, 'r') as f:
            content = f.read()
        
        # Pattern for traditional for loops over containers
        pattern = r'for\s*\(\s*(?:auto|int|size_t)\s+(\w+)\s*=\s*0\s*;\s*\1\s*<\s*(\w+)\.size\(\)\s*;\s*(?:\+\+\1|\1\+\+)\s*\)'
        
        def replace_loop(match):
            var_name = match.group(1)
            container = match.group(2)
            return f'for (auto& item : {container})'
        
        content = re.sub(pattern, replace_loop, content)
        
        with open(cpp_file, 'w') as f:
            f.write(content)
    
    def _add_override(self, cpp_file, mod_data):
        """Add override keyword to virtual functions"""
        with open(cpp_file, 'r') as f:
            lines = f.readlines()
        
        modified_lines = []
        in_class = False
        
        for line in lines:
            # Detect class declaration
            if re.match(r'^\s*class\s+\w+', line):
                in_class = True
            elif re.match(r'^\s*};', line):
                in_class = False
            
            # Add override to virtual functions
            if in_class and 'virtual' in line and 'override' not in line:
                if ';' in line:  # Function declaration
                    line = re.sub(r';', ' override;', line)
            
            modified_lines.append(line)
        
        with open(cpp_file, 'w') as f:
            f.writelines(modified_lines)
    
    def _replace_ms_specific(self, cpp_file, mod_data):
        """Replace Microsoft-specific syntax with standard C++"""
        with open(cpp_file, 'r') as f:
            content = f.read()
        
        replacements = {
            r'__forceinline': 'inline',
            r'__declspec\(dllexport\)': '[[gnu::visibility("default")]]',
            r'__declspec\(dllimport\)': '[[gnu::visibility("default")]]',
            r'__stdcall': '',
            r'__cdecl': '',
            r'__fastcall': '',
            r'__try': 'try',
            r'__except': 'catch',
            r'__finally': '',
            r'_int64': 'long long',
            r'__int64': 'long long',
            r'__int32': 'int',
            r'__int16': 'short',
            r'__int8': 'char',
        }
        
        for pattern, replacement in replacements.items():
            content = re.sub(r'\b' + pattern + r'\b', replacement, content)
        
        with open(cpp_file, 'w') as f:
            f.write(content)
    
    def _apply_custom_mod(self, cpp_file, mod_data):
        """Apply a custom modification from mod_data"""
        # This would handle custom modifications passed in mod_data
        # For now, it's a placeholder for cppDev-provided changes
        
        if 'changes' in mod_data:
            with open(cpp_file, 'r') as f:
                content = f.read()
            
            for change in mod_data['changes']:
                if change['type'] == 'replace':
                    content = content.replace(change['old'], change['new'])
                elif change['type'] == 'regex':
                    content = re.sub(change['pattern'], change['replacement'], content)
            
            with open(cpp_file, 'w') as f:
                f.write(content)
    
    def create_mod_from_diff(self, original_file, modified_file):
        """Create a mod from the difference between two files"""
        with open(original_file, 'r') as f:
            original = f.read()
        
        with open(modified_file, 'r') as f:
            modified = f.read()
        
        # Analyze differences to determine mod type
        changes = []
        
        # Check for inline removal
        if 'inline' in original and 'inline' not in modified:
            return {'mod_type': 'remove_inline'}
        
        # Check for const additions
        const_count_orig = original.count('const')
        const_count_mod = modified.count('const')
        if const_count_mod > const_count_orig:
            return {'mod_type': 'add_const'}
        
        # Check for MS-specific replacements
        if any(ms in original for ms in ['__forceinline', '__declspec', '__stdcall']):
            return {'mod_type': 'replace_ms_specific'}
        
        # Otherwise, create custom mod
        return {
            'mod_type': 'custom',
            'changes': [
                {
                    'type': 'replace',
                    'old': original,
                    'new': modified
                }
            ]
        }
    
    def validate_mod(self, cpp_file, mod_data):
        """Validate that a mod can be safely applied"""
        try:
            # Try to apply the mod to a temporary copy
            temp_file = Path(tempfile.mktemp(suffix='.cpp'))
            shutil.copy2(cpp_file, temp_file)
            
            self.apply_mod(temp_file, mod_data)
            
            # Basic validation: file should still be valid C++
            # (In a real implementation, this would compile and check)
            
            temp_file.unlink()
            return True, "Mod can be applied"
            
        except Exception as e:
            return False, str(e)
    
    def get_mod_history(self):
        """Get the history of applied mods"""
        return self.mod_history
    
    def export_mod(self, mod_data, output_path):
        """Export a mod to a file for sharing"""
        with open(output_path, 'w') as f:
            json.dump(mod_data, f, indent=2)
    
    def import_mod(self, mod_path):
        """Import a mod from a file"""
        with open(mod_path, 'r') as f:
            return json.load(f)
