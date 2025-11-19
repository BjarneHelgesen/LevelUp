# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LevelUp is a Flask-based server that modernizes legacy C++ code with zero regression risk. The system:
- Applies code transformations called "Mods" to legacy C++ codebases
- Validates changes using assembly comparison and other validators
- Ensures no regressions through multiple validation strategies
- Operates entirely offline (no internet access required for LLMs or data)
- Supports multiple concurrent cppDevs (C++ developers) working on same or different repos

**Critical Design Principle**: All code modernization must be regression-free. The system prioritizes correctness over all other concerns.

## Development Commands

### Running the Server
```bash
python server/app.py
```
Server runs on `http://0.0.0.0:5000` by default.

### Dependencies
```bash
pip install -r requirements.txt
```

## Architecture Overview

The codebase is organized into two main packages:
- **`core/`** - Core business logic (mods, validators, compilers, processing)
- **`server/`** - Flask web server (app, templates, static files)

See package-specific CLAUDE.md files for detailed documentation:
- `core/CLAUDE.md` - Core business logic components and patterns
- `server/CLAUDE.md` - Web server, API, and UI details

### High-Level Component Interaction

```
User (Web UI)
    ↓ JSON with string IDs
server/app.py (Boundary Layer)
    ↓ Type-safe objects (enums, dataclasses)
core/ModProcessor
    ↓ orchestrates
core/Repo + core/ModHandler + core/Compiler + core/Validators
    ↓ returns
core/Result (type-safe)
    ↓ converts to JSON
User (Web UI)
```

**Key Architectural Decision**: String IDs only exist at the API boundary (`server/app.py`). All internal code uses type-safe enums and objects for better error detection and IDE support.

## Data Flow

**Submitting a Mod** (end-to-end):
1. Frontend sends JSON with mod details
2. `server/app.py` converts JSON to type-safe `ModRequest` object
3. For BUILTIN mods: creates mod instance via factory (only place string IDs used)
4. Mod queued with unique UUID, initial `Result` object created
5. `core/ModProcessor` processes in worker thread:
   - Clone/pull repo → checkout work branch
   - Apply mod based on source type (BUILTIN/COMMIT)
   - Compile original → compile modified → validate
   - If valid: commit to work branch; if invalid: hard reset
6. Returns `Result` object with SUCCESS/FAILED status
7. Frontend polls for status updates via `/api/mods/{mod_id}/status`

**Validation Flow**:
1. Compile original source to assembly
2. Apply mod transformation
3. Compile modified source to assembly
4. Validator compares outputs (e.g., ASMValidator compares normalized assembly)
5. Result object contains validation details per file

## Validation Types

The system supports multiple validators:
- **ASM comparison**: Exact same assembly output (currently implemented)
- **AST diff**: Abstract syntax tree comparison (planned)
- **Source diff**: Expected source-level changes only (planned)
- **Unit tests**: Same results across all inputs (planned)
- **Human validator**: For non-obvious cases requiring judgment (manual)

## Mod Types

**Built-in Mods** (see Mods.md for full list):
- Remove inline keywords
- Add const correctness
- Modernize for loops (range-based)
- Add override keywords
- Replace MS-specific syntax with standards-compliant alternatives

**Custom Mods**:
- CppDev commits (validated and rebased)
- Regex-based transformations

## Important Constraints

1. **Cross-platform**: Write cross-platform code; initially runs on Windows
2. **No internet**: All operations must work without internet access
3. **Simplicity over beauty**: Prioritize code correctness and simplicity
4. **No regressions**: Primary objective - validated changes must be functionally identical
5. **Compute-intensive OK**: Prefer more validations if it ensures correctness
6. **Extensible**: Architecture allows adding new compilers, validators, and editing tools

## Type Safety Pattern

**String IDs only at API boundary**:
- Frontend sends/receives JSON with string IDs (e.g., `"mod_type": "remove_inline"`)
- `server/app.py` converts strings to enums/objects immediately
- `core` package uses only type-safe objects:
  - `ModRequest` with `ModSourceType` enum (not "builtin" string)
  - `Result` with `ResultStatus` enum (not "success" string)
  - Mod instances from factory (not string IDs)
- `server/app.py` converts back to JSON with string IDs for frontend responses
- Pattern prevents typos and provides IDE autocomplete

**Example Flow**:
```python
# Frontend: {"type": "builtin", "mod_type": "remove_inline"}
# server/app.py converts:
from core.mod_request import ModRequest, ModSourceType
from core.mods.mod_factory import ModFactory

source_type = ModSourceType.BUILTIN
mod_instance = ModFactory.from_id("remove_inline")  # Only string usage
mod_request = ModRequest(source_type=source_type, mod_instance=mod_instance)
# Backend uses mod_request.source_type (enum) and mod_request.mod_instance (object)
```

## Code Style

**Minimal Documentation**:
- Codebase prioritizes clarity through simple, readable code over verbose documentation
- Docstrings removed unless they provide non-obvious information
- Important warnings preserved (e.g., "IMPORTANT: Stable identifier used in APIs")
- Code should be self-documenting through clear naming and structure

## Workflow

**Always Commit Changes**: After completing any code changes (not just planning), always commit them. Each prompt that results in code modifications should end with a commit.

**Git Commands**: Run any git commands that don't require the `-f` (force) flag without asking for permission.

## Working with the Codebase

- Workspace directory `workspace/` created on first run, contains repos and temp files
- Repository configurations stored in JSON at `workspace/repos.json`
- Each mod gets unique UUID for tracking through queue/results lifecycle
- All git operations happen in cloned repos under `workspace/repos/{repo_name}/`

For detailed information about specific packages, see:
- `core/CLAUDE.md` - How to add validators, mods, compilers; internal architecture
- `server/CLAUDE.md` - API endpoints, web UI, configuration, workspace management
