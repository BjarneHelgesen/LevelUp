"""
AddFunctionQualifier refactoring - adds a qualifier to a function.
"""

from typing import Optional

from .refactoring_base import RefactoringBase
from .refactoring_params import AddFunctionQualifierParams
from ..git_commit import GitCommit
from .. import logger


class AddFunctionQualifier(RefactoringBase):
    """
    Add qualifier (const, noexcept, override, etc.) to a function.
    """

    def get_probability_of_success(self) -> float:
        """Safe refactoring: adding qualifiers preserves semantics - high confidence."""
        return 0.9

    def apply(self, params: AddFunctionQualifierParams) -> Optional[GitCommit]:
        """
        Add qualifier to specific function at given line number.

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

            # Check if qualifier already exists
            if params.qualifier in line:
                return None

            # Check if we can add qualifier
            if ';' not in line:
                return None

            # Modify line - add qualifier before semicolon
            modified_line = line.replace(';', f' {params.qualifier};', 1)
            lines[params.line_number - 1] = modified_line

            # Write modified content
            params.file_path.write_text(''.join(lines), encoding='utf-8')

            # Invalidate symbols for this file
            self._invalidate_symbols(params.file_path)

            # Create commit message (no line number in message)
            commit_msg = f"Add {params.qualifier} to {params.function_name} in {params.file_path.name}"

            # Create and return GitCommit
            return GitCommit(
                repo=self.repo,
                commit_message=commit_msg,
                validator_type=params.validator_type,
                affected_symbols=[params.function_name],
                probability_of_success=self.get_probability_of_success()
            )

        except Exception as e:
            logger.error(f"Failed to add {params.qualifier} to {params.function_name}: {e}")
            return None
