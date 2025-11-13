"""
Base Validator class for LevelUp
Defines the interface for all validator implementations
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Tuple


class BaseValidator(ABC):
    """Abstract base class for validator implementations"""

    @staticmethod
    @abstractmethod
    def get_id() -> str:
        """
        Get the stable identifier for this validator

        IMPORTANT: This string is used in APIs and databases. Do not change once set.

        Returns:
            Stable identifier string
        """
        pass

    @staticmethod
    @abstractmethod
    def get_name() -> str:
        """
        Get the human-readable name of the validator

        Returns:
            Human-readable name of the validator
        """
        pass

    @abstractmethod
    def validate(self, original_file: Path, modified_file: Path) -> bool:
        """
        Validate that the modified file is regression-free compared to the original

        Args:
            original_file: Path to the original file (or its compiled artifact)
            modified_file: Path to the modified file (or its compiled artifact)

        Returns:
            True if validation passes (no regressions), False otherwise
        """
        pass

    @abstractmethod
    def get_diff_report(self, original_file: Path, modified_file: Path) -> str:
        """
        Generate a detailed diff report between original and modified files

        Args:
            original_file: Path to the original file
            modified_file: Path to the modified file

        Returns:
            String containing the diff report
        """
        pass

    def get_validation_details(self, original_file: Path, modified_file: Path) -> Dict[str, Any]:
        """
        Get detailed validation information (optional to override)

        Args:
            original_file: Path to the original file
            modified_file: Path to the modified file

        Returns:
            Dictionary containing validation details
        """
        is_valid = self.validate(original_file, modified_file)
        return {
            'valid': is_valid,
            'validator_type': self.__class__.__name__
        }
