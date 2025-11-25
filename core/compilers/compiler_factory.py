from typing import List, Dict, Any

from .base_compiler import BaseCompiler
from .msvc_compiler import MSVCCompiler
from .clang_compiler import ClangCompiler

from config import COMPILER_TYPE, CompilerType


# Singleton instance cache
_compiler_instance = None


def get_compiler() -> BaseCompiler:
    """Get the configured compiler instance.

    Returns the appropriate compiler based on COMPILER_TYPE setting in config.py.
    This is the ONLY place in the codebase that should branch on compiler type.
    """
    global _compiler_instance

    if _compiler_instance is not None:
        return _compiler_instance

    if COMPILER_TYPE == CompilerType.MSVC:
        _compiler_instance = MSVCCompiler()
    elif COMPILER_TYPE == CompilerType.CLANG:
        _compiler_instance = ClangCompiler()
    else:
        raise ValueError(f"Unsupported compiler type: {COMPILER_TYPE}")

    return _compiler_instance


def reset_compiler():
    """Reset compiler instance (for testing only)."""
    global _compiler_instance
    _compiler_instance = None


class CompilerFactory:
    @staticmethod
    def get_available_compilers() -> List[Dict[str, Any]]:
        return [
            {'id': MSVCCompiler.get_id().value, 'name': MSVCCompiler.get_name()},
            {'id': ClangCompiler.get_id().value, 'name': ClangCompiler.get_name()},
        ]
