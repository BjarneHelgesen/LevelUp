"""
Base Mod class for LevelUp
Defines the interface for all code modification implementations
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional


class BaseMod(ABC):
    """Abstract base class for mod implementations"""

    def __init__(self, mod_id: str, description: str):
        """
        Initialize the mod

        Args:
            mod_id: Unique identifier for this mod
            description: Human-readable description of what the mod does
        """
        self.mod_id = mod_id
        self.description = description

    @staticmethod
    @abstractmethod
    def get_id() -> str:
        """
        Get the stable identifier for this mod

        IMPORTANT: This string is used in APIs and databases. Do not change once set.

        Returns:
            Stable identifier string
        """
        pass

    @staticmethod
    @abstractmethod
    def get_name() -> str:
        """
        Get the human-readable name of the mod

        Returns:
            Human-readable name of the mod
        """
        pass

    @abstractmethod
    def apply(self, source_file: Path) -> Path:
        """
        Apply the modification to a source file

        Args:
            source_file: Path to the source file to modify

        Returns:
            Path to the modified file (may be the same file or a temporary copy)
        """
        pass

    @abstractmethod
    def can_apply(self, source_file: Path) -> bool:
        """
        Check if this mod can be applied to the given source file

        Args:
            source_file: Path to the source file

        Returns:
            True if the mod can be applied, False otherwise
        """
        pass

    def validate_before_apply(self, source_file: Path) -> tuple[bool, str]:
        """
        Validate that the mod can be safely applied (optional to override)

        Args:
            source_file: Path to the source file

        Returns:
            Tuple of (is_valid, message)
        """
        if not source_file.exists():
            return False, f"Source file does not exist: {source_file}"

        if not self.can_apply(source_file):
            return False, f"Mod {self.mod_id} cannot be applied to {source_file}"

        return True, "Validation passed"

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this mod (optional to override)

        Returns:
            Dictionary containing mod metadata
        """
        return {
            'mod_id': self.mod_id,
            'description': self.description,
            'mod_type': self.__class__.__name__
        }
