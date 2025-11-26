"""
MS_MacroReplacement - replaces Microsoft-specific keywords with macros.
"""

import re
from pathlib import Path
from typing import Generator, Tuple

from .base_mod import BaseMod


class MSMacroReplacementMod(BaseMod):
    """
    Repo-wide mod that replaces Microsoft-specific keywords with macros.

    NOTE: Currently stubbed out - needs dedicated refactoring implementations.
    """

    def __init__(self):
        super().__init__(
            mod_id='ms_macro_replacement',
            description='Replace MS-specific keywords with macros'
        )

    @staticmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return 'ms_macro_replacement'

    @staticmethod
    def get_name() -> str:
        return 'MS Macro Replacement'

    def generate_refactorings(self, repo, symbols):
        """
        Generate refactorings to replace MS-specific keywords with macros.

        TODO: Implement dedicated refactorings for MS macro replacements.
        """
        # Stub: Return no refactorings for now
        return
        yield  # Make this a generator
