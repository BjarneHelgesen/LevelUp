"""
Abstract base class for refactorings.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional
from pathlib import Path

if TYPE_CHECKING:
    from ..repo.repo import Repo
    from ..doxygen.symbol_table import SymbolTable
    from ..git_commit import GitCommit
    from .refactoring_params import RefactoringParams


class RefactoringBase(ABC):
    """
    Abstract base class for refactorings.

    Refactorings are atomic code transformations that:
    1. Validate preconditions
    2. Modify file(s) in-place
    3. Create a git commit
    4. Invalidate affected symbols
    5. Return GitCommit object on success, None on failure

    Subclasses implement apply() taking a typed RefactoringParams subclass.
    """

    def __init__(self, repo: 'Repo', symbols: 'SymbolTable'):
        self.repo = repo
        self.symbols = symbols

    def apply(self, params: 'RefactoringParams') -> Optional['GitCommit']:
        """
        Apply this refactoring with typed parameters.

        Args:
            params: Typed parameter object specific to this refactoring

        Returns:
            GitCommit object if successful, None if refactoring cannot be applied
        """
        raise NotImplementedError("Subclasses must implement apply()")

    @abstractmethod
    def get_probability_of_success(self) -> float:
        """
        Return estimated probability that this refactoring will be valid (0.0-1.0).

        High values (e.g., 0.9) indicate safe refactorings with high confidence.
        Low values (e.g., 0.1) indicate speculative changes with low confidence.

        This probability is used to determine when to validate batches of commits.
        Probabilities are multiplied together; validation happens when product falls
        below threshold (e.g., 0.8), ensuring likely successful batches with minimal
        risk of deep rollbacks.

        Returns:
            Probability of success (0.0-1.0)
        """
        pass

    def _invalidate_symbols(self, file_path: Path):
        """Helper to invalidate symbols for a modified file."""
        self.symbols.invalidate_file(file_path)
