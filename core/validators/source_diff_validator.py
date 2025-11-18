import difflib
from pathlib import Path
from typing import List

from .base_validator import BaseValidator
from ..compiled_file import CompiledFile


class SourceDiffValidator(BaseValidator):
    def __init__(self, compiler=None, allowed_removals: List[str] = None):
        self.allowed_removals = allowed_removals or ['inline']

    @staticmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return 'source_diff'

    @staticmethod
    def get_name() -> str:
        return "Source Diff Validator"

    def validate(self, original_file: Path, modified_file: Path) -> bool:
        original_content = original_file.read_text(encoding='utf-8', errors='ignore')
        modified_content = modified_file.read_text(encoding='utf-8', errors='ignore')
        return self._validate_content(original_content, modified_content)

    def validate_compiled_files(self, original: CompiledFile, modified: CompiledFile) -> bool:
        original_content = original.source_file.read_text(encoding='utf-8', errors='ignore')
        modified_content = modified.source_file.read_text(encoding='utf-8', errors='ignore')
        return self._validate_content(original_content, modified_content)

    def _validate_content(self, original_content: str, modified_content: str) -> bool:
        # Check that removing allowed words from original produces modified
        expected = original_content
        for word in self.allowed_removals:
            expected = expected.replace(word, '')

        # Normalize whitespace for comparison
        expected_normalized = ' '.join(expected.split())
        modified_normalized = ' '.join(modified_content.split())

        return expected_normalized == modified_normalized

    def get_diff_report(self, original_file: Path, modified_file: Path) -> str:
        original_content = original_file.read_text(encoding='utf-8', errors='ignore')
        modified_content = modified_file.read_text(encoding='utf-8', errors='ignore')

        diff = difflib.unified_diff(
            original_content.splitlines(),
            modified_content.splitlines(),
            fromfile=str(original_file),
            tofile=str(modified_file),
            lineterm=''
        )

        return '\n'.join(diff)

    def get_diff_report_compiled(self, original: CompiledFile, modified: CompiledFile) -> str:
        return self.get_diff_report(original.source_file, modified.source_file)
