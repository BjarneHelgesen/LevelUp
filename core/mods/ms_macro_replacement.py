import re
from pathlib import Path
from typing import Generator, Set, Dict

from .base_mod import BaseMod


PATTERNS = {
    '__forceinline': 'LEVELUP_FORCEINLINE',
    r'__declspec\s*\(\s*dllexport\s*\)': 'LEVELUP_DECLSPEC_DLLEXPORT',
    r'__declspec\s*\(\s*dllimport\s*\)': 'LEVELUP_DECLSPEC_DLLIMPORT',
    r'__declspec\s*\(\s*nothrow\s*\)': 'LEVELUP_DECLSPEC_NOTHROW',
    r'__declspec\s*\(\s*noreturn\s*\)': 'LEVELUP_DECLSPEC_NORETURN',
    r'__declspec\s*\(\s*align\s*\(\s*(\d+)\s*\)\s*\)': r'LEVELUP_DECLSPEC_ALIGN(\1)',
    r'__declspec\s*\(\s*novtable\s*\)': 'LEVELUP_DECLSPEC_NOVTABLE',
    r'__assume\s*\(': 'LEVELUP_ASSUME(',
    '__int8': 'LEVELUP_INT8',
    '__int16': 'LEVELUP_INT16',
    '__int32': 'LEVELUP_INT32',
    '__int64': 'LEVELUP_INT64',
}


MACRO_DEFS = {
    'LEVELUP_FORCEINLINE': {
        'msvc': '__forceinline',
        'other': 'inline'
    },
    'LEVELUP_DECLSPEC_DLLEXPORT': {
        'msvc': '__declspec(dllexport)',
        'other': ''
    },
    'LEVELUP_DECLSPEC_DLLIMPORT': {
        'msvc': '__declspec(dllimport)',
        'other': ''
    },
    'LEVELUP_DECLSPEC_NOTHROW': {
        'msvc': '__declspec(nothrow)',
        'other': ''
    },
    'LEVELUP_DECLSPEC_NORETURN': {
        'msvc': '__declspec(noreturn)',
        'other': ''
    },
    'LEVELUP_DECLSPEC_ALIGN': {
        'msvc': '__declspec(align(x))',
        'other': '',
        'has_arg': True
    },
    'LEVELUP_DECLSPEC_NOVTABLE': {
        'msvc': '__declspec(novtable)',
        'other': ''
    },
    'LEVELUP_ASSUME': {
        'msvc': '__assume',
        'other': '(void)',
        'has_arg': True
    },
    'LEVELUP_INT8': {
        'msvc': '__int8',
        'other': 'int8_t',
        'needs_cstdint': True
    },
    'LEVELUP_INT16': {
        'msvc': '__int16',
        'other': 'int16_t',
        'needs_cstdint': True
    },
    'LEVELUP_INT32': {
        'msvc': '__int32',
        'other': 'int32_t',
        'needs_cstdint': True
    },
    'LEVELUP_INT64': {
        'msvc': '__int64',
        'other': 'int64_t',
        'needs_cstdint': True
    },
}


HEADER_NAME = 'levelup_msvc_compat.h'


class MSMacroReplacementMod(BaseMod):
    def __init__(self):
        super().__init__(
            mod_id='ms_macro_replacement',
            description='Replace Microsoft-specific syntax with cross-compiler macros'
        )
        self.used_macros: Set[str] = set()
        self.needs_cstdint = False

    @staticmethod
    def get_id() -> str:
        return 'ms_macro_replacement'

    @staticmethod
    def get_name() -> str:
        return 'MS Macro Replacement'

    @staticmethod
    def get_validator_id() -> str:
        return 'asm_o0'

    def generate_changes(self, repo_path: Path) -> Generator[tuple[Path, str], None, None]:
        # Find all C/C++ source and header files, sorted for deterministic order
        source_files = []
        for pattern in ['**/*.cpp', '**/*.c', '**/*.hpp', '**/*.h']:
            source_files.extend([f for f in repo_path.glob(pattern)
                                if not f.name.startswith('_levelup_')])
        source_files = sorted(source_files)

        # First pass: scan all files to determine which macros are used
        for source_file in source_files:
            self._scan_file_for_macros(source_file)

        # If no macros found, nothing to do
        if not self.used_macros:
            return

        # Generate header file
        header_path = repo_path / HEADER_NAME
        self._generate_header(header_path)
        yield (header_path, f"Add {HEADER_NAME} with macro definitions")

        # Second pass: replace MS-specific syntax in each file
        for source_file in source_files:
            yield from self._process_file(source_file)

    def _scan_file_for_macros(self, source_file: Path):
        try:
            content = source_file.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return

        # Check each pattern
        for pattern, macro_name in PATTERNS.items():
            # Extract macro name (might have \1 capture group in it)
            base_macro = macro_name.split('(')[0] if '(' in macro_name else macro_name

            # Check if pattern exists in file
            if re.search(r'\b' + pattern + r'\b', content):
                self.used_macros.add(base_macro)

                # Check if this macro needs cstdint
                if MACRO_DEFS.get(base_macro, {}).get('needs_cstdint'):
                    self.needs_cstdint = True

    def _generate_header(self, header_path: Path):
        lines = []
        lines.append('#ifndef LEVELUP_MSVC_COMPAT_H')
        lines.append('#define LEVELUP_MSVC_COMPAT_H')
        lines.append('')

        # Add cstdint include if needed
        if self.needs_cstdint:
            lines.append('#include <cstdint>')
            lines.append('')

        lines.append('#ifdef _MSC_VER')
        lines.append('  // MSVC: Use native Microsoft extensions')

        # MSVC definitions
        for macro in sorted(self.used_macros):
            if macro in MACRO_DEFS:
                macro_def = MACRO_DEFS[macro]
                msvc_val = macro_def['msvc']

                if macro_def.get('has_arg'):
                    # Handle macros with arguments
                    if macro == 'LEVELUP_DECLSPEC_ALIGN':
                        lines.append(f'  #define {macro}(x) __declspec(align(x))')
                    elif macro == 'LEVELUP_ASSUME':
                        lines.append(f'  #define {macro}(expr) __assume(expr)')
                else:
                    lines.append(f'  #define {macro} {msvc_val}')

        lines.append('#else')
        lines.append('  // Clang/GCC: Use standards-compliant or best-effort equivalents')

        # Clang/GCC definitions
        for macro in sorted(self.used_macros):
            if macro in MACRO_DEFS:
                macro_def = MACRO_DEFS[macro]
                other_val = macro_def['other']

                if macro_def.get('has_arg'):
                    if macro == 'LEVELUP_DECLSPEC_ALIGN':
                        lines.append(f'  #define {macro}(x)')
                    elif macro == 'LEVELUP_ASSUME':
                        lines.append(f'  #define {macro}(expr) (void)(expr)')
                else:
                    lines.append(f'  #define {macro} {other_val}')

        lines.append('#endif')
        lines.append('')
        lines.append('#endif // LEVELUP_MSVC_COMPAT_H')
        lines.append('')

        header_path.write_text('\n'.join(lines), encoding='utf-8')

    def _process_file(self, source_file: Path) -> Generator[tuple[Path, str], None, None]:
        try:
            content = source_file.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return

        # Check if this file needs any replacements
        needs_changes = False
        for pattern in PATTERNS.keys():
            if re.search(r'\b' + pattern + r'\b', content):
                needs_changes = True
                break

        if not needs_changes:
            return

        # Add include at the top if not already present
        include_line = f'#include "{HEADER_NAME}"'
        if include_line not in content:
            # Find first non-comment, non-whitespace line
            lines = content.split('\n')
            insert_pos = 0

            # Skip leading comments and whitespace
            in_block_comment = False
            for i, line in enumerate(lines):
                stripped = line.strip()

                # Track block comments
                if '/*' in stripped:
                    in_block_comment = True
                if '*/' in stripped:
                    in_block_comment = False
                    insert_pos = i + 1
                    continue

                # Skip empty lines and line comments
                if in_block_comment or not stripped or stripped.startswith('//'):
                    insert_pos = i + 1
                    continue

                # Found first real line
                break

            lines.insert(insert_pos, include_line)
            content = '\n'.join(lines)
            source_file.write_text(content, encoding='utf-8')
            yield (source_file, f"Add {HEADER_NAME} include to {source_file.name}")

        # Process each pattern one match at a time
        for pattern, macro_name in PATTERNS.items():
            while True:
                content = source_file.read_text(encoding='utf-8', errors='ignore')

                # Skip replacements inside string literals and comments
                content_cleaned = self._remove_strings_and_comments(content)

                # Find first match in cleaned content
                regex = re.compile(r'\b' + pattern + r'\b')
                match = regex.search(content_cleaned)

                if not match:
                    break

                # Calculate line number
                line_num = content_cleaned[:match.start()].count('\n') + 1

                # Apply replacement to original content at same position
                modified_content = content[:match.start()] + regex.sub(macro_name, content[match.start():match.end()], count=1) + content[match.end():]

                source_file.write_text(modified_content, encoding='utf-8')

                # Yield this atomic change
                ms_keyword = content[match.start():match.end()]
                commit_msg = f"Replace '{ms_keyword}' with {macro_name.split('(')[0]} at {source_file.name}:{line_num}"
                yield (source_file, commit_msg)

    def _remove_strings_and_comments(self, content: str) -> str:
        # Replace string literals with spaces
        result = re.sub(r'"(?:[^"\\]|\\.)*"', lambda m: ' ' * len(m.group(0)), content)
        result = re.sub(r"'(?:[^'\\]|\\.)*'", lambda m: ' ' * len(m.group(0)), result)

        # Replace block comments with spaces
        result = re.sub(r'/\*.*?\*/', lambda m: ' ' * len(m.group(0)), result, flags=re.DOTALL)

        # Replace line comments with spaces
        result = re.sub(r'//[^\n]*', lambda m: ' ' * len(m.group(0)), result)

        return result
