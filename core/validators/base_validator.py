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

    @abstractmethod
    def validate(self, original: CompiledFile, modified: CompiledFile) -> bool:
        pass
