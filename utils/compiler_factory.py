"""
Compiler Factory for LevelUp
Creates compiler instances based on compiler type
"""

from pathlib import Path
from typing import Optional

from .base_compiler import BaseCompiler
from .compiler import MSVCCompiler


class CompilerFactory:
    """Factory for creating compiler instances"""

    @staticmethod
    def create_compiler(compiler_type: str, compiler_path: str) -> BaseCompiler:
        """
        Create a compiler instance

        Args:
            compiler_type: Type of compiler ('msvc', 'gcc', 'clang', etc.)
            compiler_path: Path to the compiler executable

        Returns:
            Compiler instance

        Raises:
            ValueError: If compiler_type is not supported
        """
        compiler_type = compiler_type.lower()

        if compiler_type == 'msvc':
            return MSVCCompiler(cl_path=compiler_path)
        elif compiler_type == 'gcc':
            # Placeholder for GCC support
            raise NotImplementedError("GCC compiler not yet implemented")
        elif compiler_type == 'clang':
            # Placeholder for Clang support
            raise NotImplementedError("Clang compiler not yet implemented")
        else:
            raise ValueError(f"Unsupported compiler type: {compiler_type}")

    @staticmethod
    def get_supported_compilers():
        """Get list of supported compiler types"""
        return ['msvc']  # 'gcc', 'clang' to be added later
