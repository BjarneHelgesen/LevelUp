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
python app.py
```
Server runs on `http://0.0.0.0:5000` by default.

### Dependencies
```bash
pip install -r requirements.txt
```

## Architecture Overview

### Core Components

**Flask Server (app.py)**
- Main entry point and API server
- Manages async mod queue using Python's `queue.Queue` and threading
- Routes defined: `/api/repos`, `/api/mods`, `/api/queue/status`, `/api/available/*`
- Uses a single worker thread (`mod_worker`) to process mods from queue
- Results stored in-memory dict `results: Dict[str, Result]` keyed by mod_id
- Factory pattern with enums for compilers, mods, and validators
- **String IDs only used here**: Converts JSON to type-safe objects (ModRequest) for backend

**ModProcessor Class (mod_processor.py)**
- Processes mods asynchronously in separate module
- Orchestrates: Repo → ModHandler → Compiler → Validators
- Each mod goes through: clone/pull → checkout work branch → apply changes → validate → commit or revert
- Returns `Result` object (not dict) for type safety
- Uses only enums and objects internally - no string IDs

**Result Class (result.py)**
- Type-safe result tracking with `ResultStatus` enum (QUEUED, PROCESSING, SUCCESS, FAILED, ERROR)
- Replaces dict-based results for better error detection
- `to_dict()` method for JSON serialization to frontend
- Raises `TypeError` if status is not a `ResultStatus` enum value

**ModRequest Class (mod_request.py)**
- Type-safe mod processing request with `ModSourceType` enum (BUILTIN, COMMIT, PATCH)
- Replaces dict-based mod_data for type safety
- Validates required fields in `__post_init__` (e.g., mod_instance for BUILTIN)
- Used internally by backend - app.py converts JSON to ModRequest

**Repo Class (repo.py)**
- Unified repository management merging all git operations
- Combines repository metadata with git command execution
- Fields: url, work_branch, repo_path, git_path, post_checkout
- Methods: ensure_cloned(), prepare_work_branch(), cherry_pick(), apply_patch(), commit(), reset_hard()
- Executes post_checkout commands automatically after branch operations
- Static method `get_repo_name()` extracts repo name from URL

### Factory Pattern

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

### Module Organization

**repo.py**
- Unified repository and git operations class
- Wrapper around git commands via subprocess
- Operations: clone, pull, checkout, cherry-pick, apply patch, commit, rebase, reset
- All operations use `_run_git()` helper with `subprocess.run()`
- Includes repository metadata and post-checkout hook execution

**utils/git_handler.py** (Legacy - being phased out in favor of Repo)
- Original git wrapper - functionality merged into Repo class
- May still be referenced in some places during transition

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

### Code Style

**Minimal Documentation**:
- Codebase prioritizes clarity through simple, readable code over verbose documentation
- Docstrings removed unless they provide non-obvious information
- Important warnings preserved (e.g., "IMPORTANT: Stable identifier used in APIs")
- Code should be self-documenting through clear naming and structure

### Web UI Architecture

**Frontend (templates/index.html + static/js/app.js)**
- Screen-based navigation: Repos screen → Mods screen (with back button)
- Modal dialog for adding repositories
- No SPA framework - uses vanilla JavaScript with fetch API
- Forms submit to Flask API endpoints
- Real-time status updates via polling for queue and mod status
- Dynamically loads available mods from `/api/available/mods`

**State Management (static/js/app.js)**
- `selectedRepo` tracks current working repository
- `currentRepos` array synchronized with server
- Clicking repo navigates to Mods screen
- Polling intervals for queued mods updates while on Mods screen

### Data Flow

1. **Adding a Repository**:
   - User submits repo URL, work branch, build commands
   - Server extracts repo name from URL
   - Config saved to `workspace/repos.json`
   - Repo becomes selectable for mod operations

2. **Submitting a Mod**:
   - Frontend sends JSON with mod details
   - app.py converts JSON to `ModRequest` object with `ModSourceType` enum
   - For BUILTIN mods: creates mod instance via `ModFactory.from_id()` (only place string IDs used)
   - Mod queued with unique UUID
   - Initial `Result` object created with status QUEUED
   - ModProcessor picks `ModRequest` from queue in worker thread
   - Repo operations: ensure_cloned(), prepare_work_branch()
   - Apply mod based on source_type enum:
     - BUILTIN: ModHandler applies mod instance to files
     - COMMIT: Repo.cherry_pick() applies commit
     - PATCH: Repo.apply_patch() applies patch file
   - Compile original → compile modified → validate ASM
   - If valid: commit to work branch; if invalid: hard reset
   - Returns `Result` object with SUCCESS/FAILED status
   - Status updated in `results` dict for polling

3. **Validation Flow**:
   - Compile original source to ASM
   - Apply mod transformation (via mod instance or git)
   - Compile modified source to ASM
   - ASMValidator compares normalized assembly
   - Result object with validation details per file
   - All validation logic uses objects, not dicts

## Key Configuration

**CONFIG Dict (app.py:36-43)**
- `workspace`: Base directory for all LevelUp data
- `repos`: Git repository clones location
- `temp`: Temporary files for compilation/validation
- `msvc_path`: Path to cl.exe (default: 'cl.exe')
- `git_path`: Path to git (default: 'git')

Environment variables `MSVC_PATH` and `GIT_PATH` override defaults.

ModProcessor accepts these paths in constructor - no global CONFIG access.

## Validation Types (README.md:38-47)

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
- Patch files
- Regex-based transformations

## Important Constraints

1. **Cross-platform**: Write cross-platform code; initially runs on Windows
2. **No internet**: All operations must work without internet access
3. **Simplicity over beauty**: Prioritize code correctness and simplicity
4. **No regressions**: Primary objective - validated changes must be functionally identical
5. **Compute-intensive OK**: Prefer more validations if it ensures correctness
6. **Extensible**: Architecture allows adding new compilers, validators, and editing tools

## Working with the Codebase

- Workspace directory `workspace/` created on first run, contains repos and temp files
- Repository configurations stored in JSON at `workspace/repos.json`
- Each mod gets unique UUID for tracking through queue/results lifecycle
- Worker thread runs continuously, processing queue with `queue.get(timeout=1)`
- Frontend polls `/api/mods/{mod_id}/status` every 2s for active mods
- All git operations happen in cloned repos under `workspace/repos/{repo_name}/`

### Type Safety Pattern

**String IDs only in app.py**:
- Frontend sends/receives JSON with string IDs (e.g., `"mod_type": "remove_inline"`)
- app.py converts strings to enums/objects immediately
- Backend code uses only type-safe objects:
  - `ModRequest` with `ModSourceType` enum (not "builtin" string)
  - `Result` with `ResultStatus` enum (not "success" string)
  - Mod instances from factory (not string IDs)
- app.py converts back to JSON with string IDs for frontend responses
- Pattern prevents typos and provides IDE autocomplete

**Example Flow**:
```python
# Frontend: {"type": "builtin", "mod_type": "remove_inline"}
# app.py converts:
source_type = ModSourceType.BUILTIN
mod_instance = ModFactory.from_id("remove_inline")  # Only string usage
mod_request = ModRequest(source_type=source_type, mod_instance=mod_instance)
# Backend uses mod_request.source_type (enum) and mod_request.mod_instance (object)
```

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
- Check `results[mod_id]` Result object for status enum: QUEUED → PROCESSING → SUCCESS/FAILED/ERROR
- Result.validation_results array contains per-file validation outcomes
- Failed validations include diff details for debugging
- Result.to_dict() serializes to JSON for frontend

**Key Files and Their Roles**:
- `app.py`: Web layer - converts JSON ↔ type-safe objects
- `mod_processor.py`: Business logic - processes ModRequest, returns Result
- `repo.py`: Git operations with repository context
- `result.py`: Type-safe result tracking with status enum
- `mod_request.py`: Type-safe mod request with source type enum
- `mods/mod_handler.py`: Applies mod instances to files
- `*_factory.py`: Convert string IDs to instances (only used in app.py)
