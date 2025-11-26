"""
AddOverrideMod - adds override keyword to virtual member functions.
"""

import re
from pathlib import Path

from .base_mod import BaseMod
from ..refactorings.add_function_qualifier import AddFunctionQualifier
from ..refactorings.refactoring_params import AddFunctionQualifierParams
from ..refactorings.qualifier_type import QualifierType


class AddOverrideMod(BaseMod):
    """
    Repo-wide mod that adds 'override' keywords to virtual functions.
    Uses simple pattern matching to identify virtual member functions.
    """

    def __init__(self):
        super().__init__(
            mod_id='add_override',
            description='Add override keyword to virtual functions'
        )

    @staticmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return 'add_override'

    @staticmethod
    def get_name() -> str:
        return 'Add Override Keywords'

    def generate_refactorings(self, repo, symbols):
        """
        Find all virtual member functions without 'override' keyword.
        Generate AddFunctionQualifier refactoring for each.
        """
        # Create refactoring instance (shared for all applications)
        refactoring = AddFunctionQualifier(repo, symbols)

        # Find all C/C++ source and header files
        source_files = []
        for pattern in ['**/*.cpp', '**/*.c', '**/*.hpp', '**/*.h']:
            source_files.extend([f for f in repo.repo_path.glob(pattern)
                                if not f.name.startswith('_levelup_')])

        for source_file in source_files:
            lines = source_file.read_text(encoding='utf-8', errors='ignore').splitlines(keepends=True)

            in_class = False
            for line_num, line in enumerate(lines, start=1):
                # Detect class declaration
                if re.match(r'^\s*class\s+\w+', line):
                    in_class = True
                elif re.match(r'^\s*};', line):
                    in_class = False

                # Check if this line needs override keyword
                if in_class and 'virtual' in line and 'override' not in line and ';' in line:
                    # Extract function name (simple heuristic)
                    function_name = self._extract_function_name(line)
                    if not function_name:
                        continue

                    # Generate refactoring parameters (typed!)
                    params = AddFunctionQualifierParams(
                        file_path=Path(source_file),
                        function_name=function_name,
                        qualifier=QualifierType.OVERRIDE,
                        line_number=line_num,
                        validator_type='asm_o0'
                    )

                    yield (refactoring, params)

    def _extract_function_name(self, line: str) -> str:
        """Extract function name from declaration line."""
        # Simple pattern: look for identifier before '('
        match = re.search(r'\b(\w+)\s*\(', line)
        if match:
            return match.group(1)
        return ''
