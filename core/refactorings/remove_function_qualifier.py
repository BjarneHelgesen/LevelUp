"""
RemoveFunctionQualifier refactoring - removes a qualifier from a function.
"""

from pathlib import Path
from typing import Optional
import re

from .refactoring_base import RefactoringBase
from ..git_commit import GitCommit
from .. import logger


class RemoveFunctionQualifier(RefactoringBase):
    """
    Remove qualifier (inline, static, etc.) from a function.
    """

    def apply(self, file_path: Path, function_name: str,
              qualifier: str, line_number: int,
              validator_type: str) -> Optional[GitCommit]:
        """
        Remove qualifier from specific function at given line number.

        Args:
            file_path: File containing the function
            function_name: Name of function to modify
            qualifier: Qualifier to remove (e.g., 'inline', 'static')
            line_number: Line number where function is declared
            validator_type: Validator type ID (e.g., "asm_o0", "asm_o3")

        Returns:
            GitCommit object if successful, None if refactoring cannot be applied
        """
        try:
            if not file_path.exists():
                return None

            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines(keepends=True)

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

            # Invalidate symbols for this file
            self._invalidate_symbols(file_path)

            # Create commit message (no line number in message)
            commit_msg = f"Remove {qualifier} from {function_name} in {file_path.name}"

            # Create and return GitCommit
            return GitCommit(
                repo=self.repo,
                commit_message=commit_msg,
                validator_type=validator_type,
                affected_symbols=[function_name]
            )

        except Exception as e:
            logger.error(f"Failed to remove {qualifier} from {function_name}: {e}")
            return None
