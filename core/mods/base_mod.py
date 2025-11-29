"""
Abstract base class for mods.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Generator, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..refactorings.base_refactoring import BaseRefactoring
    from ..refactorings.refactoring_params import RefactoringParams
    from ..parsers.symbol_table import SymbolTable
    from ..repo.repo import Repo


class BaseMod(ABC):
    """
    Abstract base class for mods.

    Mods are high-level, repo-wide transformations that:
    1. Analyze symbol table to find refactoring opportunities
    2. Generate refactorings with parameters
    3. Refactorings handle actual code modification and validation
    """

    def __init__(self, mod_id: str, description: str):
        self.mod_id = mod_id
        self.description = description

    @staticmethod
    @abstractmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        pass

    @staticmethod
    @abstractmethod
    def get_name() -> str:
        """Human-readable name for UI."""
        pass

    @abstractmethod
    def generate_refactorings(self, repo: 'Repo', symbols: 'SymbolTable') -> \
            Generator[Tuple['BaseRefactoring', 'RefactoringParams'], None, None]:
        """
        Generate refactorings for this mod.

        Args:
            repo: Repository being modified
            symbols: Symbol table for the repository

        Yields:
            Tuples of (refactoring_instance, symbol, qualifier, ...)

        Example:
            from ..refactorings.add_function_qualifier import AddFunctionQualifier
            from ..refactorings.qualifier_type import QualifierType

            # Get symbol from symbol table or create mock for testing
            symbol = symbols.get_symbol('myFunc')

            refactoring = AddFunctionQualifier(repo)
            yield (refactoring, symbol, QualifierType.CONST)
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        return {
            'mod_id': self.mod_id,
            'description': self.description,
            'mod_type': self.__class__.__name__
        }
