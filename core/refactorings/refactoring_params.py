"""
Typed parameter classes for refactorings.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class RefactoringParams:
    """
    Base class for refactoring parameters.

    Each refactoring defines its own concrete parameter class
    to ensure type safety and avoid string-indexed dictionaries.
    """

    def __init__(self, file_path: Path, validator_type: str):
        """
        Initialize base parameters common to all refactorings.

        Args:
            file_path: File to be modified
            validator_type: Validator ID (e.g., "asm_o0", "asm_o3", "source_diff")
        """
        self.file_path = file_path
        self.validator_type = validator_type


class AddFunctionQualifierParams(RefactoringParams):
    """
    Parameters for AddFunctionQualifier refactoring.
    """

    def __init__(
        self,
        file_path: Path,
        function_name: str,
        qualifier: str,
        line_number: int,
        validator_type: str
    ):
        super().__init__(file_path, validator_type)
        self.function_name = function_name
        self.qualifier = qualifier
        self.line_number = line_number


class RemoveFunctionQualifierParams(RefactoringParams):
    """
    Parameters for RemoveFunctionQualifier refactoring.
    """

    def __init__(
        self,
        file_path: Path,
        function_name: str,
        qualifier: str,
        line_number: int,
        validator_type: str
    ):
        super().__init__(file_path, validator_type)
        self.function_name = function_name
        self.qualifier = qualifier
        self.line_number = line_number
