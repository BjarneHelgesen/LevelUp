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
- Processes mods asynchronously
- Orchestrates: Repo → ModHandler → Compiler → Validators
- Each mod goes through: clone/pull → checkout work branch → apply changes → validate → commit or revert
- Returns `Result` object (not dict) for type safety
- Uses only enums and objects internally - no string IDs

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
- Generates function dependency data for repositories using Doxygen XML output
- `DoxygenRunner`: Runs Doxygen with XML output enabled, macro expansion disabled
- `DoxygenParser`: Parses Doxygen XML to extract function prototypes, file locations, and call graphs
- `FunctionInfo`: Data class holding function metadata (name, qualified_name, file_path, line_number, parameters, calls, called_by)
- Automatically runs when adding new repositories
- Mods can use this data to reduce error rates by understanding function dependencies

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
- `from_id()` creates validator instance from stable ID string
- `get_available_validators()` returns list with id and name for each validator
- Each validator class has static `get_id()` and `get_name()` methods

## Module Details

**compilers/compiler.py**
- MSVC compiler wrapper (cl.exe)
- Auto-discovers Visual Studio installation via vswhere.exe
- Key method: `compile_file()` returns `CompiledFile` with assembly output
- Uses `/FA` flag for assembly generation, `/O2` for optimization
- `CompiledFile` class (compiled_file.py) holds source_file and asm_output (string content)

**validators/asm_validator.py**
- Assembly comparison validator (primary regression detection method)
- `ASMValidatorO0` and `ASMValidatorO3` classes for different optimization levels
- Both inherit from `BaseASMValidator` which contains shared comparison logic
- `validate(original: CompiledFile, modified: CompiledFile)` compares assembly outputs
- Extracts and compares function bodies by structure:
  - `_extract_functions()` parses PROC/ENDP blocks from assembly
  - `_normalize_body()` canonicalizes identifiers (mangled names, labels, data refs)
  - `_function_bodies_match()` compares normalized function bodies
- Handles COMDAT functions (inline functions that linker can discard)
- Conservative approach: rejects changes if function bodies don't match exactly

**mods/mod_handler.py**
- Minimal orchestration class with single method: `apply_mod_instance()`
- Takes mod instance directly (no string IDs)
- Delegates to mod classes: RemoveInlineMod, AddOverrideMod, ReplaceMSSpecificMod
- Each mod class modifies files in-place via `apply()` method (returns None)
- Records mod history with metadata from each mod instance

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
2. Implement abstract methods: `get_id()`, `get_name()`, `apply(source_file: Path) -> None`
3. Add to `ModType` enum in `mods/mod_factory.py`
4. ID from `get_id()` is automatically available in UI via `/api/available/mods`
5. Pattern: modify source file in-place, `validate_before_apply()` checks if file exists

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

## Key Files

- `mod_processor.py`: Business logic - processes ModRequest, returns Result
- `repo.py`: Git operations with repository context
- `result.py`: Type-safe result tracking with status enum
- `mod_request.py`: Type-safe mod request with source type enum
- `mods/mod_handler.py`: Applies mod instances to files
- `*_factory.py`: Convert string IDs to instances (only used in server/app.py)
- `doxygen/doxygen_runner.py`: Runs Doxygen to generate XML output
- `doxygen/doxygen_parser.py`: Parses Doxygen XML for function dependency information
