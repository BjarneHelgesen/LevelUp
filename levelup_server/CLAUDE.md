# levelup_server Package

This package contains the Flask web server and UI for LevelUp.

## Package Overview

The `levelup_server` package implements:
- Flask API server with REST endpoints
- Async mod queue management using threading
- JSON ↔ type-safe object conversion (boundary layer)
- Static web UI with vanilla JavaScript
- Real-time status polling

**Key Role**: This is the only place where string IDs are used. The server converts between JSON (with string IDs) and type-safe objects (enums, dataclasses) used by the `levelup_core` package.

## Flask Server (app.py)

**Core Responsibilities**:
- Main entry point and API server
- Manages async mod queue using Python's `queue.Queue` and threading
- Uses a single worker thread (`mod_worker`) to process mods from queue
- Results stored in-memory dict `results: Dict[str, Result]` keyed by mod_id
- Converts JSON to type-safe objects via factories (CompilerFactory, ModFactory, ValidatorFactory)
- **String IDs only used here**: Converts JSON to type-safe objects (ModRequest) for backend

**API Routes**:
- `/api/repos` - List and add repositories
- `/api/mods` - Submit mod requests
- `/api/mods/<mod_id>/status` - Poll mod status
- `/api/queue/status` - View queue state
- `/api/available/mods` - List available mod types
- `/api/available/validators` - List available validators
- `/api/available/compilers` - List available compilers

**Worker Thread**:
- Runs continuously with `queue.get(timeout=1)`
- Processes mods using ModProcessor from `levelup_core` package
- Updates `results` dict with Result objects
- Each mod gets unique UUID for tracking through queue/results lifecycle

## Configuration

**CONFIG Dict (app.py:36-43)**
- `workspace`: Base directory for all LevelUp data
- `repos`: Git repository clones location
- `temp`: Temporary files for compilation/validation
- `msvc_path`: Path to cl.exe (default: 'cl.exe')
- `git_path`: Path to git (default: 'git')

Environment variables `MSVC_PATH` and `GIT_PATH` override defaults.

ModProcessor accepts these paths in constructor - no global CONFIG access in `levelup_core` package.

## Web UI Architecture

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
- Frontend polls `/api/mods/{mod_id}/status` every 2s for active mods

## Data Flow Through Server Layer

**Adding a Repository**:
1. User submits repo URL, work branch, build commands
2. Server extracts repo name from URL using `Repo.get_repo_name()`
3. Config saved to `workspace/repos.json`
4. Repo becomes selectable for mod operations

**Submitting a Mod**:
1. Frontend sends JSON with mod details
2. app.py converts JSON to `ModRequest` object with `ModSourceType` enum
3. For BUILTIN mods: creates mod instance via `ModFactory.from_id()` (only place string IDs used)
4. Mod queued with unique UUID
5. Initial `Result` object created with status QUEUED
6. Returns mod_id to frontend for polling

**Processing and Status Updates**:
1. ModProcessor picks `ModRequest` from queue in worker thread
2. Processing updates Result status: QUEUED → PROCESSING → SUCCESS/FAILED/ERROR
3. Status updated in `results` dict
4. Frontend polls endpoint to retrieve updated Result via `result.to_dict()`

## Type Safety at API Boundary

**String IDs only in app.py**:
- Frontend sends/receives JSON with string IDs (e.g., `"mod_type": "remove_inline"`)
- app.py converts strings to enums/objects immediately
- Backend code (levelup_core package) uses only type-safe objects:
  - `ModRequest` with `ModSourceType` enum (not "builtin" string)
  - `Result` with `ResultStatus` enum (not "success" string)
  - Mod instances from factory (not string IDs)
- app.py converts back to JSON with string IDs for frontend responses
- Pattern prevents typos and provides IDE autocomplete

**Example Conversion Flow**:
```python
# Frontend: {"type": "builtin", "mod_type": "remove_inline"}
# app.py converts:
from levelup_core.mod_request import ModRequest, ModSourceType
from levelup_core.mods.mod_factory import ModFactory

source_type = ModSourceType.BUILTIN
mod_instance = ModFactory.from_id("remove_inline")  # Only string usage
mod_request = ModRequest(source_type=source_type, mod_instance=mod_instance)
# Backend uses mod_request.source_type (enum) and mod_request.mod_instance (object)
```

## Workspace Management

- Workspace directory `workspace/` created on first run
- Repository configurations stored in JSON at `workspace/repos.json`
- All git operations happen in cloned repos under `workspace/repos/{repo_name}/`
- Temp files for compilation/validation stored in `workspace/temp/`

## Key Files

- `app.py`: Web layer - converts JSON ↔ type-safe objects, manages queue
- `templates/index.html`: Main UI template
- `static/js/app.js`: Frontend JavaScript with state management and API calls
- `static/css/style.css`: UI styling
