import re
from pathlib import Path

from .base_mod import BaseMod


class ReplaceMSSpecificMod(BaseMod):
    def __init__(self):
        super().__init__(
            mod_id='replace_ms_specific',
            description='Replace Microsoft-specific syntax with standard C++'
        )
        self.replacements = {
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

    @staticmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return 'replace_ms_specific'

    @staticmethod
    def get_name() -> str:
        return 'Replace MS-Specific Syntax'

    def apply(self, source_file: Path) -> None:
        # Modify file in-place
        with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        for pattern, replacement in self.replacements.items():
            content = re.sub(r'\b' + pattern + r'\b', replacement, content)

        with open(source_file, 'w', encoding='utf-8') as f:
            f.write(content)
