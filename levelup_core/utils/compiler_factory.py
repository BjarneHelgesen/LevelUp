from enum import Enum
from typing import List, Dict, Any

from .base_compiler import BaseCompiler
from .compiler import MSVCCompiler


class CompilerType(Enum):
    MSVC = MSVCCompiler


class CompilerFactory:
    @staticmethod
    def from_id(compiler_id: str, compiler_path: str) -> BaseCompiler:
        for compiler_type in CompilerType:
            if compiler_type.value.get_id() == compiler_id:
                return compiler_type.value(cl_path=compiler_path)
        raise ValueError(f"Unsupported compiler: {compiler_id}")

    @staticmethod
    def get_available_compilers() -> List[Dict[str, Any]]:
        return [
            {
                'id': compiler_type.value.get_id(),
                'name': compiler_type.value.get_name()
            }
            for compiler_type in CompilerType
        ]
