"""
Abstract base class for refactorings.
"""

from abc import ABC
from typing import TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from ..repo.repo import Repo
    from ..doxygen.symbol_table import SymbolTable


class RefactoringBase(ABC):
    """
    Abstract base class for refactorings.

    Refactorings are atomic code transformations that:
    1. Validate preconditions
    2. Modify file(s) in-place
    3. Create a git commit
    4. Invalidate affected symbols
    5. Return GitCommit object on success, None on failure

    Subclasses implement apply() with named parameters specific to the refactoring.
    """

    def __init__(self, repo: 'Repo', symbols: 'SymbolTable'):
        self.repo = repo
        self.symbols = symbols

    # NOTE: Subclasses implement apply() with their own named parameters
    # Base class does not define abstract apply() to allow parameter flexibility

    def _invalidate_symbols(self, file_path: Path):
        """Helper to invalidate symbols for a modified file."""
        self.symbols.invalidate_file(file_path)
