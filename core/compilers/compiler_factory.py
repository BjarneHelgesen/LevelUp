from typing import List, Dict, Any

from .compiler_type import CompilerType
from .base_compiler import BaseCompiler
from .msvc_compiler import MSVCCompiler
from .clang_compiler import ClangCompiler


# Singleton instance cache
_compiler_instance = None
_compiler_type = CompilerType.CLANG  # Default compiler


def get_compiler() -> BaseCompiler:
    """Get the configured compiler instance.

    Returns the appropriate compiler based on the configured compiler type.
    This is the ONLY place in the codebase that should branch on compiler type.
    """
    global _compiler_instance, _compiler_type

    if _compiler_instance is not None:
        return _compiler_instance

    if _compiler_type == CompilerType.MSVC:
        _compiler_instance = MSVCCompiler()
    elif _compiler_type == CompilerType.CLANG:
        _compiler_instance = ClangCompiler()
    else:
        raise ValueError(f"Unsupported compiler type: {_compiler_type}")

    return _compiler_instance


def reset_compiler():
    """Reset compiler instance (for testing only)."""
    global _compiler_instance
    _compiler_instance = None


def set_compiler(compiler_id: str):
    """Set the active compiler by ID.

    Args:
        compiler_id: Compiler ID string ('msvc' or 'clang')

    Raises:
        ValueError: If compiler_id is not recognized
    """
    global _compiler_type, _compiler_instance

    # Convert string ID to enum
    try:
        _compiler_type = CompilerType(compiler_id)
    except ValueError:
        raise ValueError(f"Unknown compiler ID: {compiler_id}. Valid options: {[ct.value for ct in CompilerType]}")

    # Reset singleton to force re-creation with new type
    _compiler_instance = None


class CompilerFactory:
    @staticmethod
    def get_available_compilers() -> List[Dict[str, Any]]:
        return [
            {'id': MSVCCompiler.get_id().value, 'name': MSVCCompiler.get_name()},
            {'id': ClangCompiler.get_id().value, 'name': ClangCompiler.get_name()},
        ]
