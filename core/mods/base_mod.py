from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Generator


class BaseMod(ABC):
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
        pass

    @abstractmethod
    def generate_changes(self, repo_path: Path) -> Generator[tuple[Path, str], None, None]:
        """
        Generate atomic changes for this mod.
        Yields tuples of (file_path, commit_message) for each atomic change.
        The file should be modified in-place before yielding.
        The caller will compile, validate, and commit/revert each change.
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        return {
            'mod_id': self.mod_id,
            'description': self.description,
            'mod_type': self.__class__.__name__
        }
