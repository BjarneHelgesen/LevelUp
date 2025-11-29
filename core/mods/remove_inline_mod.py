"""
RemoveInlineMod - removes inline keywords from functions.
"""

from pathlib import Path
import re

from .base_mod import BaseMod
from ..refactorings.remove_function_qualifier import RemoveFunctionQualifier
from ..refactorings.qualifier_type import QualifierType
from ..parsers.symbol import Symbol, SymbolKind


class RemoveInlineMod(BaseMod):
    """
    Repo-wide mod that removes 'inline' keywords from functions.
    """

    def __init__(self):
        super().__init__(
            mod_id='remove_inline',
            description='Remove inline keywords from functions'
        )

    @staticmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return 'remove_inline'

    @staticmethod
    def get_name() -> str:
        return 'Remove Inline Keywords'

    def generate_refactorings(self, repo, symbols):
        """
        Find all inline keywords and generate RemoveFunctionQualifier refactoring for each.
        """
        # Create refactoring instance (shared for all applications)
        refactoring = RemoveFunctionQualifier(repo)

        # Find all C/C++ source and header files
        source_files = []
        for pattern in ['**/*.cpp', '**/*.c', '**/*.hpp', '**/*.h']:
            source_files.extend([f for f in repo.repo_path.glob(pattern)
                                if not f.name.startswith('_levelup_')])

        for source_file in source_files:
            content = source_file.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines(keepends=True)

            # Find all 'inline' keyword occurrences
            for line_num, line in enumerate(lines, start=1):
                if re.search(r'\binline\b', line):
                    # Extract function name (simple heuristic)
                    function_name = self._extract_function_name(line)
                    if not function_name:
                        function_name = f"function_at_line_{line_num}"

                    # Create mock Symbol object for this function
                    symbol = Symbol(kind=SymbolKind.FUNCTION)
                    symbol.name = function_name
                    symbol.qualified_name = function_name
                    symbol.file_path = str(source_file)
                    symbol.line_start = line_num
                    symbol.line_end = line_num
                    symbol.prototype = line.strip()

                    # Yield refactoring with symbol and qualifier
                    yield (refactoring, symbol, QualifierType.INLINE)

    def _extract_function_name(self, line: str) -> str:
        """Extract function name from declaration line."""
        # Simple pattern: look for identifier before '(' after 'inline'
        match = re.search(r'inline.*?\b(\w+)\s*\(', line)
        if match:
            return match.group(1)
        return ''
