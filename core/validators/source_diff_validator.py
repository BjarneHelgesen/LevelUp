from typing import List

from .base_validator import BaseValidator
from ..compilers.compiled_file import CompiledFile


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

    def validate(self, original: CompiledFile, modified: CompiledFile) -> bool:
        original_content = original.source_file.read_text(encoding='utf-8', errors='ignore')
        modified_content = modified.source_file.read_text(encoding='utf-8', errors='ignore')

        # Check that removing allowed words from original produces modified
        expected = original_content
        for word in self.allowed_removals:
            expected = expected.replace(word, '')

        # Normalize whitespace for comparison
        expected_normalized = ' '.join(expected.split())
        modified_normalized = ' '.join(modified_content.split())

        return expected_normalized == modified_normalized
