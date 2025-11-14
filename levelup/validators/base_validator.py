from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any


class BaseValidator(ABC):
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
    def validate(self, original_file: Path, modified_file: Path) -> bool:
        pass

    @abstractmethod
    def get_diff_report(self, original_file: Path, modified_file: Path) -> str:
        pass

    def get_validation_details(self, original_file: Path, modified_file: Path) -> Dict[str, Any]:
        is_valid = self.validate(original_file, modified_file)
        return {
            'valid': is_valid,
            'validator_type': self.__class__.__name__
        }
