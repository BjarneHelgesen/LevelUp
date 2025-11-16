import re
import tempfile
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

    def can_apply(self, source_file: Path) -> bool:
        if not source_file.exists():
            return False

        try:
            with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return 'inline' in content
        except Exception:
            return False

    def apply(self, source_file: Path) -> Path:
        temp_file = Path(tempfile.mktemp(suffix=source_file.suffix))
        shutil.copy2(source_file, temp_file)

        with open(temp_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Pattern to match inline keyword
        pattern = r'\binline\s+'
        content = re.sub(pattern, '', content)

        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(content)

        return temp_file
