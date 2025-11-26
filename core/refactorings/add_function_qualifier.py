"""
AddFunctionQualifier refactoring - adds a qualifier to a function.
"""

from pathlib import Path
from typing import Optional

from .refactoring_base import RefactoringBase
from ..git_commit import GitCommit
from .. import logger


class AddFunctionQualifier(RefactoringBase):
    """
    Add qualifier (const, noexcept, override, etc.) to a function.
    """

    def apply(self, file_path: Path, function_name: str,
              qualifier: str, line_number: int,
              validator_type: str) -> Optional[GitCommit]:
        """
        Add qualifier to specific function at given line number.

        Args:
            file_path: File containing the function
            function_name: Name of function to modify
            qualifier: Qualifier to add (e.g., 'const', 'override')
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

            # Invalidate symbols for this file
            self._invalidate_symbols(file_path)

            # Create commit message (no line number in message)
            commit_msg = f"Add {qualifier} to {function_name} in {file_path.name}"

            # Create and return GitCommit
            return GitCommit(
                repo=self.repo,
                commit_message=commit_msg,
                validator_type=validator_type,
                affected_symbols=[function_name]
            )

        except Exception as e:
            logger.error(f"Failed to add {qualifier} to {function_name}: {e}")
            return None
