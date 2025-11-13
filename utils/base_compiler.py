from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Optional


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
    def compile(self, source_file: Path, output_file: Optional[Path] = None,
                additional_flags: Optional[List[str]] = None) -> any:
        pass

    @abstractmethod
    def compile_to_asm(self, source_file: Path, asm_output_file: Path,
                       additional_flags: Optional[List[str]] = None) -> Path:
        pass

    @abstractmethod
    def compile_to_obj(self, source_file: Path, obj_output_file: Path,
                       additional_flags: Optional[List[str]] = None) -> any:
        pass

    @abstractmethod
    def get_preprocessed(self, source_file: Path, output_file: Optional[Path] = None) -> any:
        pass

    @abstractmethod
    def check_syntax(self, source_file: Path) -> Tuple[bool, str]:
        pass

    @abstractmethod
    def get_warnings(self, source_file: Path) -> List[str]:
        pass
