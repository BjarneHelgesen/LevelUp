import re
from pathlib import Path
from typing import Generator

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

    def generate_changes(self, repo_path: Path) -> Generator[tuple[Path, str], None, None]:
        # Find all C/C++ source and header files
        source_files = []
        for pattern in ['**/*.cpp', '**/*.c', '**/*.hpp', '**/*.h']:
            source_files.extend([f for f in repo_path.glob(pattern)
                                if not f.name.startswith('_levelup_')])

        for source_file in source_files:
            content = source_file.read_text(encoding='utf-8', errors='ignore')

            # Try each replacement pattern
            for pattern, replacement in self.replacements.items():
                # Find all matches for this pattern
                regex = re.compile(r'\b' + pattern + r'\b')
                matches = list(regex.finditer(content))

                for match in matches:
                    # Calculate line number
                    line_num = content[:match.start()].count('\n') + 1

                    # Apply this specific replacement
                    modified_content = content[:match.start()] + replacement + content[match.end():]

                    # Write modified content
                    source_file.write_text(modified_content, encoding='utf-8')

                    # Yield this atomic change
                    ms_keyword = match.group(0)
                    commit_msg = f"Replace '{ms_keyword}' at {source_file.name}:{line_num}"
                    yield (source_file, commit_msg)

                    # Re-read current content for next iteration
                    content = source_file.read_text(encoding='utf-8', errors='ignore')
