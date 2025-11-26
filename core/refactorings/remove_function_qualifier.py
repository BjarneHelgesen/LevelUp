"""
RemoveFunctionQualifier refactoring - removes a qualifier from a function.
"""

from typing import Optional
import re

from .refactoring_base import RefactoringBase
from .refactoring_params import RemoveFunctionQualifierParams
from ..git_commit import GitCommit
from .. import logger


class RemoveFunctionQualifier(RefactoringBase):
    """
    Remove qualifier (inline, static, etc.) from a function.
    """

    def get_probability_of_success(self) -> float:
        """Safe refactoring: removing qualifiers like 'inline' preserves semantics - high confidence."""
        return 0.9

    def apply(self, params: RemoveFunctionQualifierParams) -> Optional[GitCommit]:
        """
        Remove qualifier from specific function at given line number.

        Args:
            params: Typed parameters containing file_path, function_name,
                   qualifier, line_number, and validator_type

        Returns:
            GitCommit object if successful, None if refactoring cannot be applied
        """
        try:
            if not params.file_path.exists():
                return None

            content = params.file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines(keepends=True)

            if params.line_number < 1 or params.line_number > len(lines):
                return None

            line = lines[params.line_number - 1]

            # Check if qualifier exists
            if params.qualifier not in line:
                return None

            # Remove the qualifier (with surrounding whitespace)
            # Match the qualifier as a whole word
            pattern = r'\b' + re.escape(params.qualifier) + r'\b\s*'
            modified_line = re.sub(pattern, '', line, count=1)

            # Only apply if something changed
            if modified_line == line:
                return None

            lines[params.line_number - 1] = modified_line

            # Write modified content
            params.file_path.write_text(''.join(lines), encoding='utf-8')

            # Invalidate symbols for this file
            self._invalidate_symbols(params.file_path)

            # Create commit message (no line number in message)
            commit_msg = f"Remove {params.qualifier} from {params.function_name} in {params.file_path.name}"

            # Create and return GitCommit
            return GitCommit(
                repo=self.repo,
                commit_message=commit_msg,
                validator_type=params.validator_type,
                affected_symbols=[params.function_name],
                probability_of_success=self.get_probability_of_success()
            )

        except Exception as e:
            logger.error(f"Failed to remove {params.qualifier} from {params.function_name}: {e}")
            return None
