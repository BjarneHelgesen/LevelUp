# core Package

This package contains the core business logic for LevelUp's code modernization system.

## Package Overview

The `core` package implements:
- Mod processing orchestration
- Repository and git operations
- Type-safe request/result handling
- Compiler abstractions
- Validators for regression detection
- Factory patterns for extensibility

**Key Principle**: All operations use type-safe objects (enums, classes) internally. String IDs only exist at the API boundary in `server/app.py`.

## Core Components

**ModProcessor (mod_processor.py)**
- Processes mods using the refactoring architecture
- Orchestrates: Repo → Doxygen → SymbolTable → Mod → Refactorings → Validation
- Initializes with configured compiler from CompilerFactory
- Each mod generates refactorings; each refactoring applies changes and creates GitCommit
- Each GitCommit goes through: compile original → apply change → compile modified → validate → keep or rollback
- Atomic branch pattern: creates temporary branch per mod, squashes commits on success
- Returns `Result` object (not dict) for type safety with SUCCESS/PARTIAL/FAILED/ERROR status
- Uses only enums and objects internally - no string IDs
- Ensures Doxygen data exists before processing (regenerates if stale)

**Result (result.py)**
- Type-safe result tracking with `ResultStatus` enum (QUEUED, PROCESSING, SUCCESS, PARTIAL, FAILED, ERROR)
- Replaces dict-based results for better error detection
- `to_dict()` method for JSON serialization to frontend
- Raises `TypeError` if status is not a `ResultStatus` enum value
- PARTIAL status used when some files pass validation but others fail

**ModRequest (mod_request.py)**
- Type-safe mod processing request with `ModSourceType` enum (BUILTIN, COMMIT)
- Replaces dict-based mod_data for type safety
- Validates required fields in `__init__` (e.g., mod_instance for BUILTIN)
- Used internally by backend - app.py converts JSON to ModRequest

**Repo (repo.py)**
- Unified repository management merging all git operations
- Combines repository metadata with git command execution
- Hardcoded work branch: "levelup-work" (WORK_BRANCH constant)
- Fields: url, repo_path, git_path, post_checkout
- Methods: ensure_cloned(), prepare_work_branch(), cherry_pick(), commit(), reset_hard()
- Executes post_checkout commands automatically after branch operations
- Static method `get_repo_name()` extracts repo name from URL
- Wrapper around git commands via subprocess
- All operations use `_run_git()` helper with `subprocess.run()`
- Doxygen integration: `generate_doxygen()`, `get_doxygen_parser()`, `get_function_info()`, `get_functions_in_file()`

**Doxygen Integration (doxygen/)**
- Generates symbol data for repositories using Doxygen XML output
- `DoxygenRunner`: Runs Doxygen with XML output enabled, macro expansion disabled
- `DoxygenParser`: Parses Doxygen XML to extract symbols (functions, classes, enums, etc.)
- `Symbol`: Class holding symbol metadata (name, qualified_name, file_path, line_start, line_end, prototype, dependencies, etc.)
- `SymbolTable`: Manages symbols with incremental invalidation (marks files dirty after modification)
- Automatically runs when adding new repositories
- Stale marker system: `.doxygen_stale` file indicates Doxygen data needs regeneration on next run
- Mods use SymbolTable to find refactoring opportunities

## Factory Pattern

All factories use the same pattern: enum-based registry with `from_id()` and `get_available_*()` methods.

**Compiler Factory (compilers/compiler_factory.py)**
- Enum-based registry: `CompilerType` enum maps to compiler classes
- `from_id()` creates compiler instance from stable ID string
- `get_available_compilers()` returns list with id and name for each compiler
- Each compiler class has static `get_id()` and `get_name()` methods

**Mod Factory (mods/mod_factory.py)**
- Enum-based registry: `ModType` enum maps to mod classes
- `from_id()` creates mod instance from stable ID string
- `get_available_mods()` returns list with id and name for each mod
- Each mod class has static `get_id()` and `get_name()` methods
- No string literals in factory - all IDs come from class methods

**Validator Factory (validators/validator_factory.py)**
- Enum-based registry: `ValidatorType` enum maps to validator classes
- `from_id(validator_id: str, compiler=None)` creates validator instance from stable ID string
- Takes optional compiler parameter; if None, uses configured compiler from `get_compiler()`
- `get_available_validators()` returns list with id and name for each validator
- Each validator class has static `get_id()`, `get_name()`, and `get_optimization_level()` methods
- Validators instantiated with compiler instance to support different compilers

## Module Details

**compilers/base_compiler.py**
- Abstract base class defining compiler interface
- Abstract methods: `get_id()`, `get_name()`, `compile_file(source_file: Path, optimization_level: int) -> CompiledFile`
- All compilers must inherit from BaseCompiler and implement these methods
- Ensures consistent interface across different compiler implementations

**compilers/msvc_compiler.py**
- MSVC compiler wrapper (cl.exe) - default compiler
- Auto-discovers Visual Studio installation via vswhere.exe
- Supports optimization levels: 0 (`/Od`), 1-3 (`/O1`, `/O2`, `/O3` mapped to `/O2`)
- Key method: `compile_file(source_file, optimization_level)` returns `CompiledFile` with assembly output
- Uses `/FA` flag for assembly generation, includes generated .asm files in temp directory
- `CompiledFile` class (compiled_file.py) holds source_file and asm_output (string content)

**compilers/clang_compiler.py**
- Clang compiler wrapper (clang.exe)
- Auto-discovers Clang installation from PATH or common install locations
- Supports optimization levels: 0 (`-O0`), 1-3 (`-O1`, `-O2`, `-O3`)
- Uses `-S -masm=intel` flags for Intel-syntax assembly output
- Compatible with same assembly parsing as MSVC for cross-compiler validation

**compilers/compiler_factory.py**
- Manages compiler selection and instantiation
- `get_compiler()`: Returns singleton instance of configured compiler (default: MSVC)
- `set_compiler(compiler_id: str)`: Changes active compiler by ID
- `from_id(compiler_id: str)`: Creates new compiler instance from ID
- CompilerType enum: MSVC, CLANG
- Configuration stored in `workspace/config.json` as `{"compiler": "msvc"}`

**validators/base_validator.py**
- Abstract base class defining validator interface
- Abstract methods: `get_id()`, `get_name()`, `get_optimization_level()`, `validate(original: CompiledFile, modified: CompiledFile) -> bool`
- All validators must inherit from BaseValidator and implement these methods
- Validators specify which compiler optimization level they require

**validators/asm_validator.py**
- Assembly comparison validator (primary regression detection method)
- `ASMValidatorO0`: Compares assembly at O0 (no optimization) - ID: `asm_o0`
- `ASMValidatorO3`: Compares assembly at O3 (full optimization) - ID: `asm_o3`
- Both inherit from `BaseASMValidator` which contains shared comparison logic
- Takes compiler instance in `__init__` to support different compilers (MSVC, Clang)
- `validate(original: CompiledFile, modified: CompiledFile)` compares assembly outputs
- Extracts and compares function bodies by structure:
  - `_extract_functions()` parses PROC/ENDP blocks from assembly
  - `_normalize_body()` canonicalizes identifiers (mangled names, labels, data refs)
  - `_function_bodies_match()` compares normalized function bodies
- Handles COMDAT functions (inline functions that linker can discard)
- Conservative approach: rejects changes if function bodies don't match exactly

**mods/base_mod.py and Mod Classes**
- `BaseMod`: Abstract base class defining mod interface
- Mods generate refactorings via `generate_refactorings(repo, symbols)` method
- Yields tuples of (refactoring_instance, *args) where args are passed to refactoring's `apply()` method
- Each mod class (RemoveInlineMod, AddOverrideMod, etc.) implements its own refactoring generation logic
- Mods typically create Symbol objects (real from SymbolTable or mock for simple pattern matching)
- Example mods: RemoveInlineMod, AddOverrideMod, ReplaceMSSpecificMod, MSMacroReplacementMod

**refactorings/**
- `RefactoringBase`: Abstract base class for atomic refactorings
- Refactorings implement `apply(*args) -> Optional[GitCommit]`
- Each refactoring modifies files in-place and creates a git commit
- Returns GitCommit object on success, None if refactoring cannot be applied
- Example refactorings: RemoveFunctionQualifier, AddFunctionQualifier
- Each refactoring specifies `get_probability_of_success()` for batch validation optimization

**git_commit.py**
- Represents a single atomic git commit created by refactorings
- Stores validator_type (e.g., "asm_o0"), affected_symbols, and probability_of_success
- `rollback()` method reverts commit if validation fails
- Used for tracking and managing individual atomic changes

## Code Style

**Minimal Documentation**:
- Codebase prioritizes clarity through simple, readable code over verbose documentation
- Docstrings removed unless they provide non-obvious information
- Important warnings preserved (e.g., "IMPORTANT: Stable identifier used in APIs")
- Code should be self-documenting through clear naming and structure

## Common Development Patterns

**Adding a New Validator**:
1. Create validator class in `validators/` inheriting from BaseValidator
2. Implement abstract methods: `get_id()`, `get_name()`, `get_optimization_level()`, `validate(original: CompiledFile, modified: CompiledFile)`
3. Add to `ValidatorType` enum in `validators/validator_factory.py`
4. ID from `get_id()` is automatically available in UI via `/api/available/validators`

**Adding a New Mod Type**:
1. Create mod class in `mods/` inheriting from BaseMod
2. Implement abstract methods:
   - `get_id()`: Stable string identifier used in API (IMPORTANT: Never change once set)
   - `get_name()`: Human-readable name for UI
   - `generate_refactorings(repo, symbols)`: Generator yielding `(refactoring_instance, *args)` tuples
3. Each yielded tuple should contain:
   - A refactoring instance (e.g., RemoveFunctionQualifier(repo))
   - Arguments that will be passed to the refactoring's `apply()` method
   - Typically: (refactoring, symbol, qualifier) or similar
4. Add to `ModType` enum in `mods/mod_factory.py`
5. ID from `get_id()` is automatically available in UI via `/api/available/mods`

**Adding a New Refactoring Type**:
1. Create refactoring class in `refactorings/` inheriting from RefactoringBase
2. Implement required methods:
   - `get_probability_of_success()`: Return float 0.0-1.0 indicating confidence (e.g., 0.9 for safe changes)
   - `apply(*args) -> Optional[GitCommit]`: Implement the transformation
3. In `apply()` method:
   - Validate preconditions (return None if cannot apply)
   - Modify file(s) in-place
   - Create and return GitCommit with validator_type and affected_symbols
   - Return None if refactoring cannot be applied
4. Each GitCommit specifies which validator to use (e.g., ValidatorId.ASM_O0)
5. Validator choice determines strictness: asm_o0 for most changes, asm_o3 for stricter validation

**Adding a New Compiler**:
1. Create compiler class in `compilers/` inheriting from BaseCompiler
2. Implement abstract methods: `get_id()`, `get_name()`, `compile_file()` returning `CompiledFile`
3. Add to `CompilerType` enum in `compilers/compiler_factory.py`
4. ID from `get_id()` is automatically available in UI via `/api/available/compilers`

**Understanding Validation Results**:
- Result object has status enum: QUEUED → PROCESSING → SUCCESS/PARTIAL/FAILED/ERROR
- Result.validation_results array contains per-file validation outcomes
- PARTIAL status when some files pass but others fail
- Result.to_dict() serializes to JSON for frontend

**validators/validator_id.py**
- Constants for validator IDs: ASM_O0, ASM_O3
- Used by refactorings to specify which validator to use when creating GitCommit
- Prefer using ValidatorId constants over raw strings for type safety

## Key Files

- `mod_processor.py`: Business logic - processes ModRequest using refactoring architecture, returns Result
- `repo.py`: Git operations with repository context
- `result.py`: Type-safe result tracking with status enum
- `mod_request.py`: Type-safe mod request with source type enum
- `git_commit.py`: Represents atomic git commits created by refactorings
- `mods/base_mod.py`: Abstract base class for mods
- `refactorings/refactoring_base.py`: Abstract base class for refactorings
- `*_factory.py`: Convert string IDs to instances (only used in server/app.py)
- `doxygen/doxygen_runner.py`: Runs Doxygen to generate XML output
- `doxygen/doxygen_parser.py`: Parses Doxygen XML to extract symbols
- `doxygen/symbol_table.py`: Manages symbols with incremental invalidation
- `doxygen/symbol.py`: Symbol data class
- `validators/validator_id.py`: Constants for validator IDs
