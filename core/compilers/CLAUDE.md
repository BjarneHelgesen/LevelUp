# Compilers Package

Compiler abstractions for compiling C++ code to assembly for validation.

## Purpose

Provides unified interface for different C++ compilers (MSVC, Clang) to compile source files to assembly for regression detection through assembly comparison.

## Key Components

**BaseCompiler (base_compiler.py)**
- Abstract base class defining compiler interface
- Required methods: `get_id()`, `get_name()`, `compile_file(source_file: Path, optimization_level: int) -> CompiledFile`

**MSVCCompiler (msvc_compiler.py)**
- MSVC compiler wrapper (cl.exe) - default compiler
- Auto-discovers Visual Studio via vswhere.exe
- Optimization levels: 0 (`/Od`), 1-3 (`/O1`, `/O2`, `/O3` → `/O2`)
- Uses `/FA` flag for Intel-syntax assembly generation

**ClangCompiler (clang_compiler.py)**
- Clang compiler wrapper (clang.exe)
- Auto-discovers from PATH or common install locations
- Optimization levels: 0 (`-O0`), 1-3 (`-O1`, `-O2`, `-O3`)
- Uses `-S -masm=intel` for Intel-syntax assembly output

**CompiledFile (compiled_file.py)**
- Data class holding compilation output
- Fields: `source_file: Path`, `asm_output: str`

**CompilerFactory (compiler_factory.py)**
- Enum-based registry using `CompilerType` enum
- `get_compiler()`: Returns singleton instance of configured compiler
- `set_compiler(compiler_id: str)`: Changes active compiler
- `from_id(compiler_id: str)`: Creates new instance from ID
- Configuration stored in `workspace/config.json`

## Adding a New Compiler

1. Create class in this folder inheriting from `BaseCompiler`
2. Implement required methods:
   - `get_id()`: Stable string identifier (IMPORTANT: Never change once set)
   - `get_name()`: Human-readable name for UI
   - `compile_file(source_file, optimization_level) -> CompiledFile`: Compile and return assembly
3. Add to `CompilerType` enum in `compiler_factory.py`
4. ID automatically available in UI via `/api/available/compilers`

## Testing

Run tests: `pytest core/compilers/tests/`

Tests verify:
- Compiler discovery
- Assembly generation for each optimization level
- Cross-platform compatibility
