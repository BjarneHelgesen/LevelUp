from pathlib import Path

from .base_mod import BaseMod


class CommitMod(BaseMod):
    """Mod that validates a cppdev's commit from the levelup-work branch"""

    def __init__(self):
        super().__init__('commit', 'Validate cppdev commit')

    @staticmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return 'commit'

    @staticmethod
    def get_name() -> str:
        return "Validate Commit"

    def apply(self, source_file: Path) -> None:
        # CommitMod doesn't apply changes - the changes come from cherry-picking
        # This is a no-op; the actual work is done by cherry-pick in mod_processor
        pass
