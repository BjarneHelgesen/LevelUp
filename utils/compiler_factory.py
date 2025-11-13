"""
Compiler Factory for LevelUp
Creates compiler instances based on compiler type
"""

from pathlib import Path
from typing import Optional, List, Dict, Any

from .base_compiler import BaseCompiler
from .compiler import MSVCCompiler


class CompilerFactory:
    """Factory for creating compiler instances"""

    # Registry of available compilers with their metadata
    _COMPILER_REGISTRY = {
        'msvc': {
            'class': MSVCCompiler,
            'name': 'Microsoft Visual C++',
            'description': 'Microsoft Visual C++ compiler (cl.exe)',
            'default_path': 'cl.exe'
        }
    }

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

        if compiler_type not in CompilerFactory._COMPILER_REGISTRY:
            raise ValueError(f"Unsupported compiler type: {compiler_type}")

        compiler_class = CompilerFactory._COMPILER_REGISTRY[compiler_type]['class']
        return compiler_class(cl_path=compiler_path)

    @staticmethod
    def get_available_compilers() -> List[Dict[str, Any]]:
        """
        Get list of available compilers with their metadata

        Returns:
            List of dictionaries containing compiler information:
            [
                {
                    'id': 'msvc',
                    'name': 'Microsoft Visual C++',
                    'description': 'Microsoft Visual C++ compiler (cl.exe)',
                    'default_path': 'cl.exe'
                },
                ...
            ]
        """
        return [
            {
                'id': compiler_id,
                'name': info['name'],
                'description': info['description'],
                'default_path': info['default_path']
            }
            for compiler_id, info in CompilerFactory._COMPILER_REGISTRY.items()
        ]
