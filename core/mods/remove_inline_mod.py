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

    def apply(self, source_file: Path) -> None:
        # Modify file in-place
        with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Apply transformation (may result in no changes if 'inline' not present)
        content = content.replace('inline', '')

        with open(source_file, 'w', encoding='utf-8') as f:
            f.write(content)
