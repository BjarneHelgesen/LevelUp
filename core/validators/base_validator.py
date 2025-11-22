from abc import ABC, abstractmethod

from ..compilers.compiled_file import CompiledFile


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

    @staticmethod
    @abstractmethod
    def get_optimization_level() -> int:
        """Returns the compiler optimization level required (0, 1, 2, or 3)."""
        pass

    @abstractmethod
    def validate(self, original: CompiledFile, modified: CompiledFile) -> bool:
        pass
