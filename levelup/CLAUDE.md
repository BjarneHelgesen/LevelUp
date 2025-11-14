# levelup Package

This package contains the core business logic for LevelUp's code modernization system.

## Package Overview

The `levelup` package implements:
- Mod processing orchestration
- Repository and git operations
- Type-safe request/result handling
- Compiler abstractions
- Validators for regression detection
- Factory patterns for extensibility

**Key Principle**: All operations use type-safe objects (enums, dataclasses) internally. String IDs only exist at the API boundary in `levelup_server/app.py`.

## Core Components

**ModProcessor (mod_processor.py)**
- Processes mods asynchronously
- Orchestrates: Repo → ModHandler → Compiler → Validators
- Each mod goes through: clone/pull → checkout work branch → apply changes → validate → commit or revert
- Returns `Result` object (not dict) for type safety
- Uses only enums and objects internally - no string IDs

**Result (result.py)**
- Type-safe result tracking with `ResultStatus` enum (QUEUED, PROCESSING, SUCCESS, FAILED, ERROR)
- Replaces dict-based results for better error detection
- `to_dict()` method for JSON serialization to frontend
- Raises `TypeError` if status is not a `ResultStatus` enum value

**ModRequest (mod_request.py)**
- Type-safe mod processing request with `ModSourceType` enum (BUILTIN, COMMIT)
- Replaces dict-based mod_data for type safety
- Validates required fields in `__post_init__` (e.g., mod_instance for BUILTIN)
- Used internally by backend - app.py converts JSON to ModRequest

**Repo (repo.py)**
- Unified repository management merging all git operations
- Combines repository metadata with git command execution
- Fields: url, work_branch, repo_path, git_path, post_checkout
- Methods: ensure_cloned(), prepare_work_branch(), cherry_pick(), commit(), reset_hard()
- Executes post_checkout commands automatically after branch operations
- Static method `get_repo_name()` extracts repo name from URL
- Wrapper around git commands via subprocess
- All operations use `_run_git()` helper with `subprocess.run()`

## Factory Pattern

All factories use the same pattern: enum-based registry with `from_id()` and `get_available_*()` methods.

**Compiler Factory (utils/compiler_factory.py)**
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

**utils/compiler.py**
- MSVC compiler wrapper (cl.exe)
- Key method: `compile_to_asm()` generates assembly output for validation
- Uses `/FA` flag for assembly generation, `/O2` for optimization
- Includes `_normalize_asm()` for removing comments/metadata before comparison
- `get_warnings()` captures warning output for warning diff validation

**validators/asm_validator.py**
- Assembly comparison validator (primary regression detection method)
- Normalizes ASM files by removing comments, timestamps, metadata
- Compares normalized assembly line-by-line
- Has sophisticated logic for acceptable differences:
  - Register substitution (different register allocation but same operations)
  - Instruction reordering (if independent)
  - NOPs and alignment changes
- Conservative approach: rejects changes if uncertain about equivalence

**mods/mod_handler.py**
- Minimal orchestration class with single method: `apply_mod_instance()`
- Takes mod instance directly (no string IDs)
- Delegates to mod classes: RemoveInlineMod, AddOverrideMod, ReplaceMSSpecificMod
- Each mod class handles its own logic via `apply()` and `can_apply()` methods
- Records mod history with metadata from each mod instance

**utils/git_handler.py** (Legacy - being phased out)
- Original git wrapper - functionality merged into Repo class
- May still be referenced in some places during transition

## Code Style

**Minimal Documentation**:
- Codebase prioritizes clarity through simple, readable code over verbose documentation
- Docstrings removed unless they provide non-obvious information
- Important warnings preserved (e.g., "IMPORTANT: Stable identifier used in APIs")
- Code should be self-documenting through clear naming and structure

## Common Development Patterns

**Adding a New Validator**:
1. Create validator class in `validators/` inheriting from BaseValidator
2. Implement abstract methods: `get_id()`, `get_name()`, `validate()`, `get_diff_report()`
3. Add to `ValidatorType` enum in `validators/validator_factory.py`
4. ID from `get_id()` is automatically available in UI via `/api/available/validators`

**Adding a New Mod Type**:
1. Create mod class in `mods/` inheriting from BaseMod
2. Implement abstract methods: `get_id()`, `get_name()`, `apply()`, `can_apply()`
3. Add to `ModType` enum in `mods/mod_factory.py`
4. ID from `get_id()` is automatically available in UI via `/api/available/mods`
5. Pattern: check `can_apply()` → create temp copy → apply transformations → return path

**Adding a New Compiler**:
1. Create compiler class in `utils/` inheriting from BaseCompiler
2. Implement abstract methods: `get_id()`, `get_name()`, `compile()`, `compile_to_asm()`, etc.
3. Add to `CompilerType` enum in `utils/compiler_factory.py`
4. ID from `get_id()` is automatically available in UI via `/api/available/compilers`

**Understanding Validation Results**:
- Result object has status enum: QUEUED → PROCESSING → SUCCESS/FAILED/ERROR
- Result.validation_results array contains per-file validation outcomes
- Failed validations include diff details for debugging
- Result.to_dict() serializes to JSON for frontend

## Key Files

- `mod_processor.py`: Business logic - processes ModRequest, returns Result
- `repo.py`: Git operations with repository context
- `result.py`: Type-safe result tracking with status enum
- `mod_request.py`: Type-safe mod request with source type enum
- `mods/mod_handler.py`: Applies mod instances to files
- `*_factory.py`: Convert string IDs to instances (only used in levelup_server/app.py)
