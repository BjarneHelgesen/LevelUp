import re
from pathlib import Path
from typing import Generator

from .base_mod import BaseMod


class AddOverrideMod(BaseMod):
    def __init__(self):
        super().__init__(
            mod_id='add_override',
            description='Add override keyword to virtual functions'
        )

    @staticmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return 'add_override'

    @staticmethod
    def get_name() -> str:
        return 'Add Override Keywords'

    def generate_changes(self, repo_path: Path) -> Generator[tuple[Path, str], None, None]:
        # Find all C/C++ source and header files
        source_files = []
        for pattern in ['**/*.cpp', '**/*.c', '**/*.hpp', '**/*.h']:
            source_files.extend([f for f in repo_path.glob(pattern)
                                if not f.name.startswith('_levelup_')])

        for source_file in source_files:
            lines = source_file.read_text(encoding='utf-8', errors='ignore').splitlines(keepends=True)

            in_class = False
            for line_num, line in enumerate(lines, start=1):
                # Detect class declaration
                if re.match(r'^\s*class\s+\w+', line):
                    in_class = True
                elif re.match(r'^\s*};', line):
                    in_class = False

                # Check if this line needs override keyword
                if in_class and 'virtual' in line and 'override' not in line and ';' in line:
                    # Store original content
                    original_lines = lines.copy()

                    # Modify this specific line
                    modified_line = re.sub(r';', ' override;', line)
                    lines[line_num - 1] = modified_line

                    # Write modified content
                    source_file.write_text(''.join(lines), encoding='utf-8')

                    # Yield this atomic change
                    commit_msg = f"Add override at {source_file.name}:{line_num}"
                    yield (source_file, commit_msg)

                    # Re-read current content for next iteration
                    # (caller may have reverted the change)
                    lines = source_file.read_text(encoding='utf-8', errors='ignore').splitlines(keepends=True)
