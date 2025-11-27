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
    ↓ Type-safe objects (enums, classes)
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
   - Ensure Doxygen data exists (regenerate if stale)
   - Load SymbolTable from Doxygen XML
   - For each refactoring from mod's `generate_refactorings(repo, symbols)`:
     - Refactoring applies change (modifies file in-place, creates GitCommit)
     - Compile original with validator's optimization level
     - Compile modified with validator's optimization level
     - Validate using validator specified in GitCommit
     - If valid: keep commit; if invalid: rollback commit
   - Squash accepted commits and push to work branch
6. Returns `Result` object with SUCCESS/PARTIAL/FAILED status
7. Frontend polls for status updates via `/api/mods/{mod_id}/status`

**Validation Flow**:
1. Refactoring specifies which validator to use when creating GitCommit (via ValidatorId constants)
2. Validator created dynamically from ValidatorFactory with configured compiler
3. For each GitCommit:
   - Compile original source with validator's optimization level
   - Refactoring has already applied transformation and created commit
   - Compile modified source with same optimization level
   - Validator compares outputs (e.g., ASMValidator compares normalized assembly)
   - Keep commit if valid, rollback if invalid
4. Result object contains validation details per file (accepted_commits, rejected_commits)

## Validation Types

The system supports multiple validators (each refactoring chooses which validator to use):
- **ASM O0 comparison** (`asm_o0`): Compares assembly at O0 optimization - useful for detecting semantic changes
- **ASM O3 comparison** (`asm_o3`): Compares assembly at O3 optimization - stricter, catches optimization-affecting changes
- **AST diff**: Abstract syntax tree comparison (planned)
- **Unit tests**: Same results across all inputs (planned)
- **Human validator**: For non-obvious cases requiring judgment (manual)

Each refactoring specifies its validator when creating GitCommit (via ValidatorId constants). The ModProcessor creates the appropriate validator from the ValidatorFactory with the configured compiler.

## Mods

- Remove inline keywords (RemoveInlineMod)
- Add override keywords (AddOverrideMod)
- Replace MS-specific syntax with standards-compliant alternatives (ReplaceMSSpecificMod)
- MS Macro Replacement (MSMacroReplacementMod)

See Mods.md for planned future mods.

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

**No Dataclasses**:
- Do NOT use `@dataclass` decorator when adding new classes
- Use regular classes with explicit `__init__` methods instead
- Type hints are encouraged, but dataclasses are avoided for simplicity

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
