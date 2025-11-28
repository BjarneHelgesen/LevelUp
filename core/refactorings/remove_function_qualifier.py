"""
RemoveFunctionQualifier refactoring - removes a qualifier from a function.
"""

from typing import Optional, TYPE_CHECKING
import re
from pathlib import Path

from .refactoring_base import RefactoringBase
from ..git_commit import GitCommit
from ..validators.validator_id import ValidatorId
from .. import logger

if TYPE_CHECKING:
    from ..doxygen.symbol import Symbol


class RemoveFunctionQualifier(RefactoringBase):
    """
    Remove qualifier (inline, static, etc.) from a function.
    """

    def get_probability_of_success(self) -> float:
        """Safe refactoring: removing qualifiers like 'inline' preserves semantics - high confidence."""
        return 0.9

    def apply(self, symbol: 'Symbol', qualifier: str) -> Optional[GitCommit]:
        """
        Remove qualifier from specific function at given line number.

        Args:
            symbol: Symbol object containing function metadata
            qualifier: Qualifier to remove (e.g., 'inline', 'static')

        Returns:
            GitCommit object if successful, None if refactoring cannot be applied
        """
        try:
            file_path = Path(symbol.file_path)
            if not file_path.is_absolute():
                file_path = self.repo.repo_path / file_path
            if not file_path.exists():
                return None

            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines(keepends=True)

            line_number = symbol.line_start
            if line_number < 1 or line_number > len(lines):
                return None

            line = lines[line_number - 1]

            # Check if qualifier exists
            if qualifier not in line:
                return None

            # Remove the qualifier (with surrounding whitespace)
            # Match the qualifier as a whole word
            pattern = r'\b' + re.escape(qualifier) + r'\b\s*'
            modified_line = re.sub(pattern, '', line, count=1)

            # Only apply if something changed
            if modified_line == line:
                return None

            lines[line_number - 1] = modified_line

            # Write modified content
            file_path.write_text(''.join(lines), encoding='utf-8')

            # Create commit message (no line number in message)
            commit_msg = f"Remove {qualifier} from {symbol.name} in {file_path.name}"

            # Create and return GitCommit (all validation with ASM O0 for now)
            return GitCommit(
                repo=self.repo,
                commit_message=commit_msg,
                validator_type=ValidatorId.ASM_O0,
                affected_symbols=[symbol.qualified_name],
                probability_of_success=self.get_probability_of_success()
            )

        except Exception as e:
            logger.error(f"Failed to remove {qualifier} from {symbol.name}: {e}")
            return None
