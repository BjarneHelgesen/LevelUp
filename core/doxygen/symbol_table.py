"""
SymbolTable class for managing symbols with incremental updates.
"""

from pathlib import Path
from typing import Dict, List, Set, Optional, TYPE_CHECKING

from .symbol import Symbol
from .. import logger

if TYPE_CHECKING:
    from ..repo.repo import Repo


class SymbolTable:
    """
    Manages symbols for a repository with incremental updates.

    Symbols are loaded from Doxygen XML and updated as files are modified.
    Uses fast incremental updates to avoid full Doxygen regeneration.
    """

    def __init__(self, repo: 'Repo'):
        self.repo = repo
        self.repo_path = repo.repo_path
        self._symbols: Dict[str, Symbol] = {}
        self._file_index: Dict[Path, Set[str]] = {}
        self._dirty_files: Set[Path] = set()
        self._needs_full_refresh = False

    def load_from_doxygen(self):
        """Initial load of all symbols from Doxygen XML."""
        logger.info("Loading symbols from Doxygen XML")

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

    def invalidate_file(self, file_path: Path):
        """
        Mark file as needing re-parse.
        Called by refactorings after modifying a file.
        """
        resolved_path = file_path.resolve()
        self._dirty_files.add(resolved_path)
        logger.debug(f"Invalidated symbols for {file_path}")

    def refresh_dirty_files(self):
        """
        Update symbols for dirty files.

        For now, marks that full Doxygen refresh is needed on next run.
        Future optimization: implement direct source parsing for incremental updates.
        """
        if not self._dirty_files:
            return

        logger.info(f"Deferring refresh of {len(self._dirty_files)} dirty files to next run")

        # Mark that full refresh needed on next run
        self._mark_stale()

        # For now, we'll keep using the current symbols during this run
        # Full refresh happens on next ModProcessor run
        self._dirty_files.clear()

    def _mark_stale(self):
        """Mark that full Doxygen refresh needed on next run."""
        marker_file = self.repo_path / 'doxygen_output' / '.doxygen_stale'
        marker_file.parent.mkdir(parents=True, exist_ok=True)
        marker_file.touch()
        logger.debug("Marked Doxygen data as stale")

    def check_and_refresh_if_stale(self):
        """Check if Doxygen is stale and regenerate if needed."""
        marker_file = self.repo_path / 'doxygen_output' / '.doxygen_stale'

        if marker_file.exists():
            logger.info("Doxygen data is stale, regenerating...")
            self.repo.generate_doxygen()
            self.load_from_doxygen()
            marker_file.unlink()
            logger.info("Doxygen data refreshed")

    def get_symbol(self, qualified_name: str, auto_refresh: bool = True) -> Optional[Symbol]:
        """
        Get symbol by qualified name.

        Args:
            qualified_name: Fully qualified symbol name
            auto_refresh: If True, refresh dirty files before lookup
        """
        if auto_refresh:
            self.refresh_dirty_files()

        return self._symbols.get(qualified_name)

    def get_symbols_in_file(self, file_path: Path, auto_refresh: bool = True) -> List[Symbol]:
        """Get all symbols defined in a file."""
        if auto_refresh:
            self.refresh_dirty_files()

        file_path = file_path.resolve()
        qual_names = self._file_index.get(file_path, set())
        return [self._symbols[qn] for qn in qual_names if qn in self._symbols]

    def get_all_symbols(self, auto_refresh: bool = True) -> List[Symbol]:
        """Get all symbols in the repository."""
        if auto_refresh:
            self.refresh_dirty_files()

        return list(self._symbols.values())

    def _build_file_index(self):
        """Build reverse index: file -> symbols."""
        self._file_index.clear()
        for qual_name, symbol in self._symbols.items():
            file_path = Path(symbol.file_path).resolve()
            if file_path not in self._file_index:
                self._file_index[file_path] = set()
            self._file_index[file_path].add(qual_name)

        logger.debug(f"Built file index with {len(self._file_index)} files")
