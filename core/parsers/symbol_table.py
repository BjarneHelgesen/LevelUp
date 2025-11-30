"""
SymbolTable class for managing symbols with incremental updates.
"""

from pathlib import Path
from typing import Dict, List, Set, Optional, TYPE_CHECKING

from .symbols import BaseSymbol
from .symbols.function_symbol import FunctionSymbol
from .symbols.symbol_kind import SymbolKind
from .. import logger

if TYPE_CHECKING:
    from ..repo.repo import Repo


class SymbolTable:
    """
    Manages symbols for a repository.

    Symbols are loaded from Doxygen XML during initialization.
    Symbols are updated in-memory when refactorings successfully modify prototypes.
    """

    def __init__(self, repo: 'Repo'):
        self.repo = repo
        self.repo_path = repo.repo_path
        self._symbols: Dict[str, BaseSymbol] = {}
        self._file_index: Dict[Path, Set[str]] = {}

    def load_from_doxygen(self):
        """
        Load all symbols from Doxygen XML.
        Generates Doxygen data if not already present.
        """
        logger.info("Loading symbols from Doxygen XML")

        # Ensure Doxygen data exists
        xml_dir = self.repo_path / 'doxygen_output' / 'xml_unexpanded'
        if not xml_dir.exists() or not list(xml_dir.glob('*.xml')):
            logger.info("Generating Doxygen data...")
            self.repo.generate_doxygen()
            logger.info("Doxygen data generated")

        # Get Doxygen parser from repo
        doxygen_parser = self.repo.get_doxygen_parser()
        if not doxygen_parser:
            logger.warning("No Doxygen data available")
            return

        # Parse all symbols from Doxygen XML
        all_symbols = doxygen_parser.parse_all_symbols()
        self._symbols = {s.qualified_name: s for s in all_symbols}
        self._build_file_index()

        logger.info(f"Loaded {len(self._symbols)} symbols")

    def get_symbol(self, qualified_name: str) -> Optional[BaseSymbol]:
        """
        Get symbol by qualified name.

        Args:
            qualified_name: Fully qualified symbol name
        """
        return self._symbols.get(qualified_name)

    def get_symbols_in_file(self, file_path: Path) -> List[BaseSymbol]:
        """Get all symbols defined in a file."""
        file_path = file_path.resolve()
        qual_names = self._file_index.get(file_path, set())
        return [self._symbols[qn] for qn in qual_names if qn in self._symbols]

    def get_all_symbols(self) -> List[BaseSymbol]:
        """Get all symbols in the repository."""
        return list(self._symbols.values())

    def update_symbol(self, updated_symbol: BaseSymbol):
        """
        Update a symbol in the table after successful refactoring.

        This method updates the in-memory symbol representation when a
        refactoring successfully modifies a symbol's prototype or other
        globally visible properties.

        Args:
            updated_symbol: The updated symbol object with new values
        """
        qualified_name = updated_symbol.qualified_name

        if qualified_name not in self._symbols:
            logger.warning(f"Attempted to update unknown symbol: {qualified_name}")
            return

        old_symbol = self._symbols[qualified_name]
        old_file_path = Path(old_symbol.file_path).resolve()
        new_file_path = Path(updated_symbol.file_path).resolve()

        # Update symbol in main dictionary
        self._symbols[qualified_name] = updated_symbol

        # Update file index if file changed
        if old_file_path != new_file_path:
            # Remove from old file index
            if old_file_path in self._file_index:
                self._file_index[old_file_path].discard(qualified_name)
                if not self._file_index[old_file_path]:
                    del self._file_index[old_file_path]

            # Add to new file index
            if new_file_path not in self._file_index:
                self._file_index[new_file_path] = set()
            self._file_index[new_file_path].add(qualified_name)

        logger.debug(f"Updated symbol: {qualified_name}")

    def refresh_symbol_from_source(self, qualified_name: str):
        """
        Refresh a function symbol's prototype by re-parsing from source file.

        This is called after a successful function prototype refactoring to update
        the in-memory symbol with the new prototype from the modified source.

        Args:
            qualified_name: Qualified name of the symbol to refresh
        """
        if qualified_name not in self._symbols:
            logger.warning(f"Attempted to refresh unknown symbol: {qualified_name}")
            return

        symbol = self._symbols[qualified_name]

        # Only refresh function symbols for now
        if symbol.kind != SymbolKind.FUNCTION:
            logger.debug(f"Skipping refresh for non-function symbol: {qualified_name}")
            return

        # Import here to avoid circular dependency
        from ..refactorings.function_prototype.prototype_utils import PrototypeParser

        # Find prototype in source file
        locations = PrototypeParser.find_prototype_locations(symbol)
        if not locations:
            logger.warning(f"Could not find prototype for symbol: {qualified_name}")
            return

        # Use the first location (typically the definition or declaration)
        location = locations[0]
        new_prototype = location.text.strip()

        # Update the symbol's prototype
        symbol.prototype = new_prototype

        # For FunctionSymbol, also update parsed components
        if isinstance(symbol, FunctionSymbol):
            new_return_type = PrototypeParser.extract_return_type(new_prototype)
            new_parameters = PrototypeParser.extract_parameters(new_prototype)

            if new_return_type is not None:
                symbol.return_type = new_return_type
                # Keep expanded version the same for now (would need Doxygen to update)
                symbol.return_type_expanded = new_return_type

            if new_parameters is not None:
                symbol.parameters = new_parameters
                # Keep expanded version the same for now
                symbol.parameters_expanded = new_parameters

        logger.debug(f"Refreshed symbol from source: {qualified_name}")

    def _build_file_index(self):
        """Build reverse index: file -> symbols."""
        self._file_index.clear()
        for qual_name, symbol in self._symbols.items():
            file_path = Path(symbol.file_path).resolve()
            if file_path not in self._file_index:
                self._file_index[file_path] = set()
            self._file_index[file_path].add(qual_name)

        logger.debug(f"Built file index with {len(self._file_index)} files")
