# core Package

Core business logic for LevelUp's code modernization system.

## Package Structure

Each subfolder has its own CLAUDE.md with complete, self-contained documentation:

- **`compilers/`** - Compiler abstractions (MSVC, Clang) for generating assembly
- **`validators/`** - Regression detection through assembly comparison
- **`mods/`** - High-level transformations that generate refactorings
- **`refactorings/`** - Atomic code changes that create validated commits
- **`parsers/`** - Doxygen integration for symbol extraction (formerly `doxygen/`)
- **`repo/`** - Repository management and git operations

See each folder's CLAUDE.md for details on adding new components, running tests, and usage patterns.

## Top-Level Files

**ModProcessor (mod_processor.py)**
- Orchestrates entire mod processing workflow
- Flow: Repo → Doxygen → SymbolTable → Mod → Refactorings → Validation
- Each refactoring: compile original → apply change → compile modified → validate → keep or rollback
- Returns type-safe `Result` object with SUCCESS/PARTIAL/FAILED/ERROR status

**Result (result.py)**
- Type-safe result tracking with `ResultStatus` enum
- `to_dict()` method for JSON serialization to frontend

**ModRequest (mod_request.py)**
- Type-safe mod processing request with `ModSourceType` enum
- Used internally by backend - `server/app.py` converts JSON to ModRequest

**GitCommit (git_commit.py)**
- Represents single atomic git commit created by refactorings
- Specifies validator_type, affected_symbols, probability_of_success
- `rollback()` method reverts commit if validation fails

## Key Principle

All operations use type-safe objects (enums, classes) internally. String IDs only exist at the API boundary in `server/app.py`.

## Factory Pattern

All factories use the same enum-based pattern:
- `from_id(id: str)`: Creates instance from stable ID string
- `get_available_*()`: Returns list with id and name for UI

Examples:
- `CompilerFactory.from_id("msvc")` → MSVCCompiler instance
- `ModFactory.from_id("remove_inline")` → RemoveInlineMod instance
- `ValidatorFactory.from_id("asm_o0", compiler)` → ASMValidatorO0 instance

## Testing

Run all core tests: `pytest core/`

Run specific package tests: `pytest core/{package}/tests/`
