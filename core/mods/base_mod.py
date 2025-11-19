from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any


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
    def apply(self, source_file: Path) -> Path:
        pass

    def validate_before_apply(self, source_file: Path) -> tuple[bool, str]:
        if not source_file.exists():
            return False, f"Source file does not exist: {source_file}"
        return True, "Validation passed"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            'mod_id': self.mod_id,
            'description': self.description,
            'mod_type': self.__class__.__name__
        }
