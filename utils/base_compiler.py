"""
Base Compiler class for LevelUp
Defines the interface for all compiler implementations
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Optional


class BaseCompiler(ABC):
    """Abstract base class for compiler implementations"""

    def __init__(self, compiler_path: str):
        """
        Initialize the compiler

        Args:
            compiler_path: Path to the compiler executable
        """
        self.compiler_path = compiler_path

    @abstractmethod
    def compile(self, source_file: Path, output_file: Optional[Path] = None,
                additional_flags: Optional[List[str]] = None) -> any:
        """
        Compile a source file

        Args:
            source_file: Path to the source file
            output_file: Optional output file path
            additional_flags: Optional additional compiler flags

        Returns:
            Compilation result
        """
        pass

    @abstractmethod
    def compile_to_asm(self, source_file: Path, asm_output_file: Path,
                       additional_flags: Optional[List[str]] = None) -> Path:
        """
        Compile source to assembly

        Args:
            source_file: Path to the source file
            asm_output_file: Path for assembly output
            additional_flags: Optional additional compiler flags

        Returns:
            Path to generated assembly file
        """
        pass

    @abstractmethod
    def compile_to_obj(self, source_file: Path, obj_output_file: Path,
                       additional_flags: Optional[List[str]] = None) -> any:
        """
        Compile source to object file

        Args:
            source_file: Path to the source file
            obj_output_file: Path for object file output
            additional_flags: Optional additional compiler flags

        Returns:
            Compilation result
        """
        pass

    @abstractmethod
    def get_preprocessed(self, source_file: Path, output_file: Optional[Path] = None) -> any:
        """
        Get preprocessed source

        Args:
            source_file: Path to the source file
            output_file: Optional output file for preprocessed source

        Returns:
            Preprocessed source or path to preprocessed file
        """
        pass

    @abstractmethod
    def check_syntax(self, source_file: Path) -> Tuple[bool, str]:
        """
        Check syntax of source file without generating output

        Args:
            source_file: Path to the source file

        Returns:
            Tuple of (is_valid, error_messages)
        """
        pass

    @abstractmethod
    def get_warnings(self, source_file: Path) -> List[str]:
        """
        Get all warnings for a source file

        Args:
            source_file: Path to the source file

        Returns:
            List of warning messages
        """
        pass
