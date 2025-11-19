from abc import ABC, abstractmethod
from pathlib import Path

from .compiled_file import CompiledFile


class BaseCompiler(ABC):
    def __init__(self, compiler_path: str):
        self.compiler_path = compiler_path

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
    def compile_file(self, source_file: Path, additional_flags: str = None) -> CompiledFile:
        pass
