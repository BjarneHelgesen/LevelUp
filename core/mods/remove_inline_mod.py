from pathlib import Path
import re
from typing import Generator

from .base_mod import BaseMod


class RemoveInlineMod(BaseMod):
    def __init__(self):
        super().__init__(
            mod_id='remove_inline',
            description='Remove inline keywords from functions'
        )

    @staticmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return 'remove_inline'

    @staticmethod
    def get_name() -> str:
        return 'Remove Inline Keywords'

    @staticmethod
    def get_validator_id() -> str:
        return 'source_diff'

    def generate_changes(self, repo_path: Path) -> Generator[tuple[Path, str], None, None]:
        # Find all C/C++ source and header files
        source_files = []
        for pattern in ['**/*.cpp', '**/*.c', '**/*.hpp', '**/*.h']:
            source_files.extend([f for f in repo_path.glob(pattern)
                                if not f.name.startswith('_levelup_')])

        for source_file in source_files:
            # Process inline occurrences one at a time, re-reading after each
            while True:
                content = source_file.read_text(encoding='utf-8', errors='ignore')

                # Find first 'inline' keyword occurrence with trailing whitespace
                match = re.search(r'\binline\b\s*', content)

                if not match:
                    break

                # Calculate line number for this match
                line_num = content[:match.start()].count('\n') + 1

                # Remove this specific inline occurrence
                modified_content = content[:match.start()] + content[match.end():]

                # Write modified content
                source_file.write_text(modified_content, encoding='utf-8')

                # Yield this atomic change
                commit_msg = f"Remove inline at {source_file.name}:{line_num}"
                yield (source_file, commit_msg)
