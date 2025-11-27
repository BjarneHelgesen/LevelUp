"""
Abstract base class for refactorings.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..repo.repo import Repo
    from ..git_commit import GitCommit


class RefactoringBase(ABC):
    """
    Abstract base class for refactorings.

    Refactorings are atomic code transformations that:
    1. Validate preconditions
    2. Modify file(s) in-place
    3. Create a git commit
    4. Return GitCommit object on success, None on failure

    Symbol invalidation is handled by the caller (e.g., ModProcessor).

    Subclasses implement apply() with their specific parameters.
    """

    def __init__(self, repo: 'Repo'):
        self.repo = repo

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
