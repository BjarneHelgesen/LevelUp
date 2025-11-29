# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Overview

LevelUp modernizes legacy C++ code with zero regression risk through validated transformations.

**Critical Design Principle**: All code modernization must be regression-free. The system prioritizes correctness over all other concerns.

## Architecture

```
User (Web UI)
    ↓ JSON with string IDs
server/app.py (API Boundary)
    ↓ Type-safe objects (enums, classes)
core/ModProcessor
    ↓ orchestrates
core packages (compilers, validators, mods, refactorings, parsers, repo)
    ↓ returns
core/Result (type-safe)
    ↓ converts to JSON
User (Web UI)
```

**Key Architectural Decision**: String IDs only exist at the API boundary (`server/app.py`). All internal code uses type-safe enums and objects for better error detection and IDE support.

## Package Documentation

See package-specific CLAUDE.md files for detailed documentation:
- **`core/`** - Core business logic (see `core/CLAUDE.md` for overview)
  - `core/compilers/` - Compiler abstractions (MSVC, Clang)
  - `core/validators/` - Regression detection through assembly comparison
  - `core/mods/` - High-level transformations
  - `core/refactorings/` - Atomic code changes
  - `core/parsers/` - Doxygen integration for symbol extraction
  - `core/repo/` - Repository management and git operations
- **`server/`** - Flask web server (API, UI, configuration)

## Development Commands

**Running the Server**:
```bash
python server/app.py
```
Server runs on `http://0.0.0.0:5000` by default.

**Install Dependencies**:
```bash
pip install -r requirements.txt
```

**Run Tests**:
```bash
pytest                    # All tests
pytest core/              # Core package tests
pytest core/validators/   # Specific package tests
```

## Code Style

**Minimal Documentation**:
- Prioritize clarity through simple, readable code over verbose documentation
- Docstrings only when providing non-obvious information
- Important warnings preserved (e.g., "IMPORTANT: Stable identifier used in APIs")

**No Dataclasses**:
- Do NOT use `@dataclass` decorator
- Use regular classes with explicit `__init__` methods
- Type hints encouraged

## Workflow

**Always Commit Changes**: After completing any code changes, always commit them.

**Git Commands**: Run any git commands that don't require the `-f` (force) flag without asking for permission.

## Important Constraints

1. **Cross-platform**: Write cross-platform code; initially runs on Windows
2. **No internet**: All operations must work offline
3. **Simplicity over beauty**: Prioritize code correctness and simplicity
4. **No regressions**: Primary objective - validated changes must be functionally identical
5. **Compute-intensive OK**: Prefer more validations if it ensures correctness
