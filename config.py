from enum import Enum


class CompilerType(Enum):
    MSVC = 'msvc'
    CLANG = 'clang'


# Compiler used for ALL Mods - change this to switch compilers
COMPILER_TYPE = CompilerType.CLANG
