"""
AddFunctionQualifier refactoring - adds a qualifier to a function.
"""

from typing import Optional, TYPE_CHECKING
from pathlib import Path

from .refactoring_base import RefactoringBase
from ..git_commit import GitCommit
from ..validators.validator_id import ValidatorId
from .. import logger

if TYPE_CHECKING:
    from ..doxygen.symbol import Symbol


class AddFunctionQualifier(RefactoringBase):
    """
    Add qualifier (const, noexcept, override, etc.) to a function.
    """

    def get_probability_of_success(self) -> float:
        """Safe refactoring: adding qualifiers preserves semantics - high confidence."""
        return 0.9

    def apply(self, symbol: 'Symbol', qualifier: str) -> Optional[GitCommit]:
        """
        Add qualifier to specific function at given line number.

        Args:
            symbol: Symbol object containing function metadata
            qualifier: Qualifier to add (e.g., 'override', 'const', 'noexcept')

        Returns:
            GitCommit object if successful, None if refactoring cannot be applied
        """
        try:
            file_path = Path(symbol.file_path)
            if not file_path.exists():
                return None

            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines(keepends=True)

            line_number = symbol.line_start
            if line_number < 1 or line_number > len(lines):
                return None

            line = lines[line_number - 1]

            # Check if qualifier already exists
            if qualifier in line:
                return None

            # Check if we can add qualifier
            if ';' not in line:
                return None

            # Modify line - add qualifier before semicolon
            modified_line = line.replace(';', f' {qualifier};', 1)
            lines[line_number - 1] = modified_line

            # Write modified content
            file_path.write_text(''.join(lines), encoding='utf-8')

            # Create commit message (no line number in message)
            commit_msg = f"Add {qualifier} to {symbol.name} in {file_path.name}"

            # Create and return GitCommit (all validation with ASM O0 for now)
            return GitCommit(
                repo=self.repo,
                commit_message=commit_msg,
                validator_type=ValidatorId.ASM_O0,
                affected_symbols=[symbol.qualified_name],
                probability_of_success=self.get_probability_of_success()
            )

        except Exception as e:
            logger.error(f"Failed to add {qualifier} to {symbol.name}: {e}")
            return None
