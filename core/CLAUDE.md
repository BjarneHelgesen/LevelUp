# core Package

Core business logic for LevelUp's code modernization system.

## Package Structure

Each subfolder has its own CLAUDE.md with complete, self-contained documentation:

- **`repo/`** - Repository management and git operations
- **`parsers/`** - parsing C++ source to a list of Symbols 
- **`compilers/`** - Compiler abstractions (MSVC, Clang) for generating assembly and verifying that the build is not broken
- **`validators/`** - Regression detection (e.g by assembly comparison)
- **`refactorings/`** - Atomic code changes that create validated commits
- **`mods/`** - High-level transformations that generate refactorings

See each folder's CLAUDE.md for details on adding new components, running tests, and usage patterns.

## Top-Level Files

**ModProcessor (mod_processor.py)**
- Orchestrates entire mod processing workflow
- Flow: Repo → Parser → SymbolTable → Mod → Refactorings → Validation
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

## Design Principles

All operations use type-safe objects (enums, classes) internally. String IDs should not exist

- Define regular classes with explicit `__init__` methods. Do NOT use `@dataclass` decorator or metaclasses
- Prefer regular classes to Dicts (key/value pairs) 
- Strings as identifiers is discouraged. Use enums, member names, etc. where possible 
- Type hints are encouraged, but not the Typing library
- All main components should inheret from an abstract base class
- All main components should be created by a factory function
- All use of main components should rely on the abstract base class - not the realization

## Factory Pattern

The web interface that uses the core package uses stringified ids. The core objects can ve created from string ids.  
- `from_id(id: str)`: Creates instance from stable ID string
- `get_available_*()`: Returns list with id and name for UI

Examples:
- `CompilerFactory.from_id("msvc")` → MSVCCompiler instance
- `ValidatorFactory.from_id("asm_o0", compiler)` → ASMValidatorO0 instance

No core code should create object from string ids. All core code should call factories with enums


## Testing

Run all core tests from top level folder: `pytest core/`
Run all core tests from the core folder: `pytest`

Run specific package tests from : `pytest {package}/tests/`
