from abc import ABC, abstractmethod
from pathlib import Path

from .compiled_file import CompiledFile
from .compiler_type import CompilerType


class BaseCompiler(ABC):
    @staticmethod
    @abstractmethod
    def get_id() -> CompilerType:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        pass

    @staticmethod
    @abstractmethod
    def get_name() -> str:
        pass

    @abstractmethod
    def compile_file(self, source_file: Path, additional_flags: str = None,
                     optimization_level: int = 2) -> CompiledFile:
        pass
