import shutil
from pathlib import Path

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

    def apply(self, source_file: Path) -> Path:
        # Create temp file in same directory as original so includes work
        temp_file = source_file.parent / f"_levelup_modified_{source_file.name}"
        shutil.copy2(source_file, temp_file)

        with open(temp_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Apply transformation (may result in no changes if 'inline' not present)
        content = content.replace('inline', '')

        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(content)

        return temp_file
