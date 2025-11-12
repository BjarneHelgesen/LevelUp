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
- Routes defined: `/api/repos`, `/api/mods`, `/api/queue/status`, `/api/cppdev/commit`
- Uses a single worker thread (`mod_worker`) to process mods from queue
- Results stored in-memory dict `results` keyed by mod_id

**ModProcessor Class (app.py:55-156)**
- Processes mods asynchronously
- Orchestrates: GitHandler → ModHandler → Compiler → Validators
- Each mod goes through: clone/pull → checkout work branch → apply changes → validate → commit or revert

### Module Organization

**utils/git_handler.py**
- Wrapper around git commands via subprocess
- Operations: clone, pull, checkout, cherry-pick, apply patch, commit, rebase, reset
- All operations use `_run_git()` helper with `subprocess.run()`

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
- Applies code transformations to C++ files
- Built-in mods: `remove_inline`, `add_const`, `modernize_for`, `add_override`, `replace_ms_specific`
- Each mod operates via regex patterns on temporary file copies
- `create_mod_from_diff()` can infer mod type from file differences

### Web UI Architecture

**Frontend (templates/index.html + static/js/app.js)**
- Tab-based interface: Repos, Mods, Queue Status, CppDev Tools
- Requires repo selection before accessing other tabs
- No SPA framework - uses vanilla JavaScript with fetch API
- Forms submit to Flask API endpoints
- Real-time status updates via polling for queue and mod status

**State Management (static/js/app.js)**
- `selectedRepo` tracks current working repository
- `currentRepos` array synchronized with server
- Repository selection enables/disables other tabs
- Polling intervals for queue status updates (5s interval)

### Data Flow

1. **Adding a Repository**:
   - User submits repo URL, work branch, build commands
   - Server extracts repo name from URL
   - Config saved to `workspace/repos.json`
   - Repo becomes selectable for mod operations

2. **Submitting a Mod**:
   - Mod queued with unique UUID
   - ModProcessor picks from queue in worker thread
   - Git operations: clone/pull, checkout work branch
   - Apply mod → compile original → compile modified → validate ASM
   - If valid: commit to work branch; if invalid: hard reset
   - Status updated in `results` dict

3. **Validation Flow**:
   - Compile original source to ASM
   - Apply mod transformation
   - Compile modified source to ASM
   - ASMValidator compares normalized assembly
   - Result stored with validation details per file

## Key Configuration

**CONFIG Dict (app.py:42-48)**
- `workspace`: Base directory for all LevelUp data
- `repos`: Git repository clones location
- `temp`: Temporary files for compilation/validation
- `msvc_path`: Path to cl.exe (default: 'cl.exe')
- `git_path`: Path to git (default: 'git')

Environment variables `MSVC_PATH` and `GIT_PATH` override defaults.

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

## Common Development Patterns

**Adding a New Validator**:
1. Create validator class in `validators/` following ASMValidator pattern
2. Add initialization in ModProcessor.__init__()
3. Add validation logic in ModProcessor.process_mod()
4. Update UI to allow selecting new validator type

**Adding a New Mod Type**:
1. Add method to ModHandler (e.g., `_modernize_xyz()`)
2. Register in `supported_mods` dict
3. Add UI option in templates/index.html builtin-mod select
4. Pattern: read file → apply regex/transformations → write file

**Understanding Validation Results**:
- Check `results[mod_id]` dict for status: queued → processing → success/failed/error
- `validation_results` array contains per-file validation outcomes
- Failed validations include diff details for debugging
