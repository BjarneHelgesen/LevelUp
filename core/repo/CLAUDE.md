# Repo Package

Repository management and git operations for code modernization workflow.

## Purpose

Unified repository abstraction that combines repository metadata with git command execution. Manages cloning, branching, commits, and post-checkout commands.

## Key Components

**Repo (repo.py)**
- Represents a single repository being modernized
- Fields:
  - `url`: Git repository URL
  - `repo_path`: Path to cloned repo in workspace (e.g., `workspace/repos/{name}`)
  - `git_path`: Working directory for git operations (usually same as repo_path)
  - `post_checkout`: Shell commands to run after branch operations (e.g., build setup)
- Hardcoded work branch: `"levelup-work"` (WORK_BRANCH constant)

## Core Methods

**Repository Setup**
- `ensure_cloned()`: Clones repo if not present, pulls latest if exists
- `prepare_work_branch()`: Creates/resets work branch from main, runs post_checkout

**Git Operations**
- `commit(message: str)`: Creates git commit with message
- `reset_hard(ref: str)`: Hard reset to specific ref (e.g., "HEAD~1")
- `cherry_pick(commit_hash: str)`: Cherry-picks commit from another branch

**Doxygen Integration**
- `generate_doxygen()`: Generates Doxygen XML output for symbol extraction
- `get_doxygen_parser()`: Returns DoxygenParser for this repo
- `get_function_info(function_name)`: Gets symbol metadata for function
- `get_functions_in_file(file_path)`: Gets all functions in file

**Utilities**
- `get_repo_name()`: Static method to extract repo name from URL

## Git Command Pattern

All git operations use `_run_git()` helper:
```python
def _run_git(self, args: list[str], check=True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=self.git_path,
        capture_output=True,
        text=True,
        check=check
    )
```

## Workflow

**Typical mod processing flow**:
1. `ensure_cloned()`: Clone or update repository
2. `prepare_work_branch()`: Create clean work branch from main
3. Mod generates refactorings
4. Each refactoring modifies files and calls `commit()`
5. Validation runs on each commit
6. Invalid commits reverted with `reset_hard("HEAD~1")`
7. Valid commits squashed and pushed to work branch

## Post-Checkout Commands

After branch operations, repo executes `post_checkout` commands:
- Useful for build system setup (e.g., `npm install`, `mkdir build && cmake ..`)
- Commands run in repo's git_path
- Failure logged but doesn't stop processing

## Testing

Run tests: `pytest core/repo/tests/`

Tests verify:
- Repository cloning and updating
- Branch creation and switching
- Commit and reset operations
- Doxygen integration
- Post-checkout command execution
- Error handling for git failures
