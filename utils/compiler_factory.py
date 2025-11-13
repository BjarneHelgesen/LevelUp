"""
Compiler Factory for LevelUp
Creates compiler instances based on compiler type
"""

from enum import Enum
from typing import List, Dict, Any

from .base_compiler import BaseCompiler
from .compiler import MSVCCompiler


class CompilerType(Enum):
    """Enum of available compiler types"""
    MSVC = MSVCCompiler


class CompilerFactory:
    """Factory for creating compiler instances"""

    @staticmethod
    def from_id(compiler_id: str, compiler_path: str) -> BaseCompiler:
        """
        Create a compiler instance from its stable ID

        Args:
            compiler_id: Stable compiler identifier (e.g., 'msvc')
            compiler_path: Path to the compiler executable

        Returns:
            Compiler instance

        Raises:
            ValueError: If compiler_id is not supported
        """
        for compiler_type in CompilerType:
            if compiler_type.value.get_id() == compiler_id:
                return compiler_type.value(cl_path=compiler_path)
        raise ValueError(f"Unsupported compiler: {compiler_id}")

    @staticmethod
    def get_available_compilers() -> List[Dict[str, Any]]:
        """
        Get list of available compilers

        Returns:
            List of dictionaries containing compiler information:
            [
                {
                    'id': 'msvc',
                    'name': 'Microsoft Visual C++'
                },
                ...
            ]
        """
        return [
            {
                'id': compiler_type.value.get_id(),
                'name': compiler_type.value.get_name()
            }
            for compiler_type in CompilerType
        ]
