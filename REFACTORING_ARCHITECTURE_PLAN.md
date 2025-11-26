# Refactoring Architecture Plan - Big Bang Migration

## Overview

This document describes the new architecture for LevelUp's code modernization system using Refactorings. This is a big-bang migration that replaces the current direct file modification pattern with a layered approach separating high-level planning (Mods) from low-level atomic transformations (Refactorings).

## Design Principles

1. **No dataclasses** - Use regular classes with explicit `__init__` methods
2. **No string identifiers** - Use enums and type-safe objects internally
3. **Separation of concerns** - Mods plan what to change, Refactorings execute changes
4. **Symbol-aware** - All refactorings have access to symbol table
5. **Doxygen required** - Symbol data always available, no optional code paths
6. **Single return value** - Refactorings return only GitCommit object (no separate metadata)

## Core Design Decision: Refactoring Class Hierarchy

### Should Refactorings Inherit from GitCommit?

**NO - Refactorings should NOT inherit from GitCommit.**

**Rationale:**
- **Semantically different concepts:** A Refactoring is a "transformation operation", a GitCommit is a "record of change"
- **Lifecycle mismatch:** Refactorings are instantiated once and applied multiple times; GitCommits are created per-application
- **Single Responsibility:** Refactorings should focus on code transformation logic, not commit tracking
- **Flexibility:** A refactoring might fail (return None) without creating a commit
- **Composition over inheritance:** Refactorings create GitCommit objects as return values

**Recommended pattern:**
```python
# Refactoring returns GitCommit, does not inherit from it
refactoring = AddFunctionQualifier(repo, symbols)
git_commit = refactoring.apply(...)  # Returns GitCommit or None
```

---

## GitCommit Class (Restored)

**File:** `core/git_commit.py`

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .repo.repo import Repo


class ValidatorType:
    """Enum for validator types."""
    ASM_O0 = "asm_o0"
    ASM_O3 = "asm_o3"


class GitCommit:
    """
    Represents a single atomic git commit.

    Created by refactorings after successfully applying a code change.
    Used for tracking commits and enabling rollback on validation failure.
    """

    def __init__(self, repo: 'Repo', commit_message: str,
                 validator_type: str, affected_symbols: list):
        """
        Create a git commit.

        Args:
            repo: Repository where commit is made
            commit_message: Commit message
            validator_type: ValidatorType constant (ASM_O0 or ASM_O3)
            affected_symbols: List of qualified symbol names affected by this change

        Raises:
            ValueError: If no changes to commit
        """
        self.repo = repo
        self.commit_message = commit_message
        self.validator_type = validator_type
        self.affected_symbols = affected_symbols if affected_symbols else []

        # Perform the commit
        if not self.repo.commit(self.commit_message):
            raise ValueError(f"No changes to commit: {commit_message}")

        self.commit_hash = self.repo.get_commit_hash()

    def rollback(self):
        """Rollback this commit (used when validation fails)."""
        self.repo.reset_hard(f'{self.commit_hash}~1')

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'commit_message': self.commit_message,
            'commit_hash': self.commit_hash,
            'validator_type': self.validator_type,
            'affected_symbols': self.affected_symbols
        }
```

**Key points:**
- Minimal fields: repo, commit_message, validator_type, affected_symbols, commit_hash
- Constructor performs the actual git commit
- `rollback()` method for reverting on validation failure
- No file_path (commits can affect multiple files)
- No optimization_level (derived from validator_type in ModProcessor)
- No refactoring_type or refactoring_params (not needed for commit tracking)

---

## ValidatorType Constants

**File:** `core/validators/validator_type.py`

```python
class ValidatorType:
    """
    Constants for validator types.
    Used instead of string literals throughout core package.
    """
    ASM_O0 = "asm_o0"
    ASM_O3 = "asm_o3"
```

**Usage:**
```python
from core.validators.validator_type import ValidatorType

# In refactorings
return GitCommit(repo, msg, ValidatorType.ASM_O0, affected_symbols)

# In ModProcessor
validator = ValidatorFactory.from_id(git_commit.validator_type)
```

---

## SymbolTable Class

**File:** `core/doxygen/symbol_table.py`

```python
from pathlib import Path
from typing import Dict, List, Set, Optional
from .symbol import Symbol


class SymbolTable:
    """
    Manages symbols for a repository with incremental updates.

    Symbols are loaded from Doxygen XML and updated as files are modified.
    """

    def __init__(self, repo_path: Path, doxygen_parser):
        self.repo_path = repo_path
        self.doxygen_parser = doxygen_parser
        self._symbols: Dict[str, Symbol] = {}
        self._file_index: Dict[Path, Set[str]] = {}
        self._dirty_files: Set[Path] = set()

    def load_from_doxygen(self):
        """Initial load of all symbols from Doxygen XML."""
        # Parse all symbols from Doxygen XML
        all_symbols = self.doxygen_parser.parse_all_symbols()
        self._symbols = {s.qualified_name: s for s in all_symbols}
        self._build_file_index()

    def invalidate_file(self, file_path: Path):
        """
        Mark file as needing re-parse.
        Called by refactorings after modifying a file.
        """
        self._dirty_files.add(file_path.resolve())

    def refresh_dirty_files(self):
        """
        Re-run Doxygen and update symbols for dirty files.
        Called before next refactoring that needs symbol data.
        """
        if not self._dirty_files:
            return

        # Re-run Doxygen on entire repo
        # (Doxygen doesn't support true incremental mode)
        self.doxygen_parser.repo.generate_doxygen()

        # Remove old symbols from dirty files
        for file_path in self._dirty_files:
            if file_path in self._file_index:
                for qual_name in self._file_index[file_path]:
                    del self._symbols[qual_name]
                del self._file_index[file_path]

        # Re-parse all symbols (Doxygen regenerated everything)
        all_symbols = self.doxygen_parser.parse_all_symbols()
        self._symbols = {s.qualified_name: s for s in all_symbols}
        self._build_file_index()

        # Clear dirty set
        self._dirty_files.clear()

    def get_symbol(self, qualified_name: str, auto_refresh: bool = True) -> Optional[Symbol]:
        """
        Get symbol by qualified name.

        Args:
            qualified_name: Fully qualified symbol name
            auto_refresh: If True, refresh dirty files before lookup
        """
        if auto_refresh:
            self.refresh_dirty_files()

        return self._symbols.get(qualified_name)

    def get_symbols_in_file(self, file_path: Path, auto_refresh: bool = True) -> List[Symbol]:
        """Get all symbols defined in a file."""
        if auto_refresh:
            self.refresh_dirty_files()

        file_path = file_path.resolve()
        qual_names = self._file_index.get(file_path, set())
        return [self._symbols[qn] for qn in qual_names if qn in self._symbols]

    def get_all_symbols(self, auto_refresh: bool = True) -> List[Symbol]:
        """Get all symbols in the repository."""
        if auto_refresh:
            self.refresh_dirty_files()

        return list(self._symbols.values())

    def _build_file_index(self):
        """Build reverse index: file -> symbols."""
        self._file_index.clear()
        for qual_name, symbol in self._symbols.items():
            file_path = Path(symbol.file_path).resolve()
            if file_path not in self._file_index:
                self._file_index[file_path] = set()
            self._file_index[file_path].add(qual_name)
```

**Key points:**
- **Lazy refresh:** Dirty files only re-parsed when `auto_refresh=True` (default)
- **Full Doxygen regeneration:** Simpler than incremental parsing
- **File-level invalidation:** Invalidate entire file, not individual symbols
- **Auto-refresh on queries:** Symbol queries trigger refresh if files are dirty

---

## RefactoringBase Abstract Class

**File:** `core/refactorings/refactoring_base.py`

```python
from abc import ABC
from typing import Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from ..git_commit import GitCommit
    from ..repo.repo import Repo
    from ..doxygen.symbol_table import SymbolTable


class RefactoringBase(ABC):
    """
    Abstract base class for refactorings.

    Refactorings are atomic code transformations that:
    1. Validate preconditions
    2. Modify file(s) in-place
    3. Create a git commit
    4. Invalidate affected symbols
    5. Return GitCommit object on success, None on failure

    Subclasses implement apply() with named parameters specific to the refactoring.
    """

    def __init__(self, repo: 'Repo', symbols: 'SymbolTable'):
        self.repo = repo
        self.symbols = symbols

    # NOTE: Subclasses implement apply() with their own named parameters
    # Base class does not define abstract apply() to allow parameter flexibility
    #
    # def apply(self, ...) -> Optional['GitCommit']:
    #     """
    #     Apply this refactoring.
    #
    #     Returns:
    #         GitCommit object if successful, None if refactoring cannot be applied
    #     """
    #     pass

    def _get_validator_type(self, is_semantic_change: bool) -> str:
        """
        Determine appropriate validator for this refactoring.

        Args:
            is_semantic_change: True if change might affect optimized assembly

        Returns:
            ValidatorType constant (ASM_O0 or ASM_O3)
        """
        from ..validators.validator_type import ValidatorType

        if is_semantic_change:
            return ValidatorType.ASM_O3
        else:
            return ValidatorType.ASM_O0

    def _invalidate_symbols(self, file_path: Path):
        """Helper to invalidate symbols for a modified file."""
        self.symbols.invalidate_file(file_path)
```

**Key points:**
- Base class provides `repo` and `symbols` to all refactorings
- `apply()` method NOT defined in base class (allows named params in subclasses)
- Helper methods for common operations (validator selection, symbol invalidation)
- Returns `Optional[GitCommit]` - None means refactoring cannot be applied

---

## Concrete Refactoring Example

**File:** `core/refactorings/add_function_qualifier.py`

```python
from pathlib import Path
from typing import Optional
import re

from .refactoring_base import RefactoringBase
from ..git_commit import GitCommit
from ..validators.validator_type import ValidatorType


class AddFunctionQualifier(RefactoringBase):
    """
    Add qualifier (const, noexcept, override, etc.) to a function.
    """

    # Semantic qualifiers that might affect optimization
    SEMANTIC_QUALIFIERS = {'const', 'noexcept', 'constexpr', 'inline'}

    # Non-semantic qualifiers (source-level only)
    NON_SEMANTIC_QUALIFIERS = {'override', 'final', 'static', 'virtual',
                               '[[nodiscard]]', '[[maybe_unused]]'}

    ALL_QUALIFIERS = SEMANTIC_QUALIFIERS | NON_SEMANTIC_QUALIFIERS

    def apply(self, file_path: Path, function_name: str,
              qualifier: str, line_number: int) -> Optional[GitCommit]:
        """
        Add qualifier to specific function at given line number.

        Args:
            file_path: File containing the function
            function_name: Name of function to modify
            qualifier: Qualifier to add (e.g., 'const', 'override')
            line_number: Line number where function is declared

        Returns:
            GitCommit object if successful, None if refactoring cannot be applied
        """
        # Validate preconditions
        if qualifier not in self.ALL_QUALIFIERS:
            return None

        if not file_path.exists():
            return None

        content = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.splitlines(keepends=True)

        if line_number < 1 or line_number > len(lines):
            return None

        line = lines[line_number - 1]

        # Check if qualifier already exists
        if qualifier in line:
            return None

        # Check if we can add qualifier (must have semicolon for simple case)
        if ';' not in line:
            return None

        # Modify line - add qualifier before semicolon
        modified_line = line.replace(';', f' {qualifier};', 1)
        lines[line_number - 1] = modified_line

        # Write modified content
        file_path.write_text(''.join(lines), encoding='utf-8')

        # Invalidate symbols for this file
        self._invalidate_symbols(file_path)

        # Determine validator based on qualifier semantics
        is_semantic = qualifier in self.SEMANTIC_QUALIFIERS
        validator_type = self._get_validator_type(is_semantic)

        # Create commit message
        commit_msg = f"Add {qualifier} to {function_name} at {file_path.name}:{line_number}"

        # Create and return GitCommit
        # GitCommit constructor performs the actual git commit
        try:
            return GitCommit(
                repo=self.repo,
                commit_message=commit_msg,
                validator_type=validator_type,
                affected_symbols=[function_name]
            )
        except ValueError:
            # No changes to commit (shouldn't happen, but defensive)
            return None
```

---

## Folder Structure

```
core/
├── git_commit.py                    # GitCommit class
├── refactorings/
│   ├── __init__.py
│   ├── refactoring_base.py          # RefactoringBase abstract class
│   ├── add_function_qualifier.py    # All refactorings in same folder
│   ├── remove_function_qualifier.py
│   ├── replace_for_with_range_for.py
│   ├── convert_to_raii.py
│   ├── replace_raw_ptr_with_smart_ptr.py
│   ├── extract_function.py
│   ├── inline_function.py
│   └── replace_ms_macro.py
├── mods/
│   ├── base_mod.py
│   ├── add_override_mod.py
│   ├── remove_inline_mod.py
│   └── ...
├── validators/
│   ├── validator_type.py            # ValidatorType constants
│   ├── ...
└── doxygen/
    ├── symbol_table.py               # SymbolTable class
    └── ...
```

**Key points:**
- All refactorings in single `refactorings/` folder (no category subfolders)
- Clear separation: refactorings/ vs mods/ vs validators/
- ValidatorType constants separate from validator implementations

---

## Updated BaseMod Interface

**File:** `core/mods/base_mod.py`

```python
from abc import ABC, abstractmethod
from typing import Generator, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..refactorings.refactoring_base import RefactoringBase
    from ..doxygen.symbol_table import SymbolTable
    from ..repo.repo import Repo


class BaseMod(ABC):
    """
    Abstract base class for mods.

    Mods are high-level, repo-wide transformations that:
    1. Analyze symbol table to find refactoring opportunities
    2. Generate refactorings with parameters
    3. Refactorings handle actual code modification and validation
    """

    def __init__(self, mod_id: str, description: str):
        self.mod_id = mod_id
        self.description = description

    @staticmethod
    @abstractmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        pass

    @staticmethod
    @abstractmethod
    def get_name() -> str:
        """Human-readable name for UI."""
        pass

    @abstractmethod
    def generate_refactorings(self, repo: 'Repo', symbols: 'SymbolTable') -> \
            Generator[Tuple['RefactoringBase', dict], None, None]:
        """
        Generate refactorings for this mod.

        Args:
            repo: Repository being modified
            symbols: Symbol table for the repository

        Yields:
            Tuples of (refactoring_instance, parameters_dict)

        Example:
            refactoring = AddFunctionQualifier(repo, symbols)
            params = {
                'file_path': Path('foo.cpp'),
                'function_name': 'myFunc',
                'qualifier': 'const',
                'line_number': 42
            }
            yield (refactoring, params)
        """
        pass

    def get_metadata(self) -> dict:
        return {
            'mod_id': self.mod_id,
            'description': self.description,
            'mod_type': self.__class__.__name__
        }
```

**Changes from old BaseMod:**
- Removed `get_validator_id()` - validator now comes from GitCommit
- Removed `generate_changes()` - replaced with `generate_refactorings()`
- Added `generate_refactorings()` yielding (refactoring, params) tuples

---

## Example Mod Implementation

**File:** `core/mods/add_override_mod.py`

```python
from pathlib import Path
from typing import Generator, Tuple

from .base_mod import BaseMod
from ..refactorings.add_function_qualifier import AddFunctionQualifier
from ..doxygen.symbol import SymbolKind


class AddOverrideMod(BaseMod):
    """
    Repo-wide mod that adds 'override' keywords to virtual functions.
    Uses Symbol system to identify virtual member functions.
    """

    def __init__(self):
        super().__init__(
            mod_id='add_override',
            description='Add override keyword to virtual member functions'
        )

    @staticmethod
    def get_id() -> str:
        return 'add_override'

    @staticmethod
    def get_name() -> str:
        return 'Add Override Keywords'

    def generate_refactorings(self, repo, symbols):
        """
        Find all virtual member functions without 'override' keyword.
        Generate AddFunctionQualifier refactoring for each.
        """
        # Create refactoring instance (shared for all applications)
        refactoring = AddFunctionQualifier(repo, symbols)

        # Get all symbols (triggers refresh of dirty files if any)
        all_symbols = symbols.get_all_symbols(auto_refresh=True)

        # Iterate through all function symbols
        for symbol in all_symbols:
            # Only process member functions
            if symbol.kind != SymbolKind.FUNCTION or not symbol.is_member:
                continue

            # Check if function is virtual but missing override
            if not self._needs_override(symbol):
                continue

            # Generate refactoring parameters
            params = {
                'file_path': Path(symbol.file_path),
                'function_name': symbol.name,
                'qualifier': 'override',
                'line_number': symbol.line_start
            }

            yield (refactoring, params)

    def _needs_override(self, symbol) -> bool:
        """Check if symbol is virtual function without override."""
        prototype = symbol.prototype.lower()

        # Must be virtual
        if 'virtual' not in prototype:
            return False

        # Must not already have override
        if 'override' in prototype:
            return False

        return True
```

---

## Updated ModProcessor

**File:** `core/mod_processor.py`

```python
from pathlib import Path
import uuid

from .compilers.compiler_factory import get_compiler
from .validators.validator_factory import ValidatorFactory
from .result import Result, ResultStatus
from .repo.repo import Repo
from .mod_request import ModRequest
from .validation_result import ValidationResult
from .doxygen.symbol_table import SymbolTable
from . import logger


class ModProcessor:
    """
    Processes mod requests using the refactoring architecture.

    All mods follow the same pattern:
    1. Ensure Doxygen data exists
    2. Load symbol table
    3. Generate refactorings from mod
    4. Apply each refactoring (creates GitCommit)
    5. Validate each commit
    6. Rollback invalid commits
    """

    def __init__(self, repos_path: Path, git_path: str = 'git'):
        logger.info(f"ModProcessor initializing with repos_path={repos_path}")
        self.compiler = get_compiler()
        self.repos_path = Path(repos_path).resolve()
        self.git_path = git_path
        logger.info("ModProcessor initialized successfully")

    def process_mod(self, mod_request: ModRequest) -> Result:
        """Process a mod request using refactorings."""
        mod_id = mod_request.id
        mod_instance = mod_request.mod_instance

        logger.info(f"Processing mod {mod_id}: {mod_instance.get_name()}")

        try:
            # Initialize repository
            repo = Repo(
                url=mod_request.repo_url,
                repos_folder=self.repos_path,
                git_path=self.git_path
            )
            repo.ensure_cloned()
            repo.prepare_work_branch()

            # Ensure Doxygen data exists
            self._ensure_doxygen_data(repo)

            # Load symbol table
            symbols = self._load_symbols(repo)

            # Process mod with refactorings
            return self._process_refactorings(mod_request, repo, symbols)

        except Exception as e:
            logger.exception(f"Error processing mod {mod_id}: {e}")
            try:
                repo.reset_hard()
            except Exception:
                pass
            return Result(
                status=ResultStatus.ERROR,
                message=str(e)
            )

    def _ensure_doxygen_data(self, repo: Repo):
        """
        Ensure Doxygen XML data exists for repo.
        Generate if missing.
        """
        # Check for unexpanded XML (primary output)
        xml_dir = repo.repo_path / 'doxygen_output' / 'xml_unexpanded'

        if not xml_dir.exists() or not list(xml_dir.glob('*.xml')):
            logger.info("Generating Doxygen data...")
            repo.generate_doxygen()
            logger.info("Doxygen data generated")
        else:
            logger.debug("Doxygen data already exists")

    def _load_symbols(self, repo: Repo) -> SymbolTable:
        """Load symbol table from Doxygen XML."""
        doxygen_parser = repo.get_doxygen_parser()
        symbols = SymbolTable(repo.repo_path, doxygen_parser)
        symbols.load_from_doxygen()
        logger.info(f"Loaded {len(symbols._symbols)} symbols from Doxygen")
        return symbols

    def _process_refactorings(self, mod_request: ModRequest,
                              repo: Repo, symbols: SymbolTable) -> Result:
        """
        Process mod using refactoring pattern.

        Each refactoring is applied, validated, and either kept or rolled back.
        """
        mod_id = mod_request.id
        mod_instance = mod_request.mod_instance

        # Create atomic branch for this mod's changes
        atomic_branch = f"levelup-atomic-{mod_id}"
        repo.create_atomic_branch(repo.work_branch, atomic_branch)

        accepted_commits = []
        rejected_commits = []
        validation_results = []

        try:
            # Generate refactorings from mod
            for refactoring, params in mod_instance.generate_refactorings(repo, symbols):
                logger.debug(f"Applying {refactoring.__class__.__name__} with params: {params}")

                # Get file path for compilation (needed before and after)
                file_path = params.get('file_path') or params.get('target_file')
                if not file_path:
                    logger.warning(f"Refactoring params missing file_path: {params}")
                    continue

                # Store original content for potential rollback
                original_content = file_path.read_text(encoding='utf-8', errors='ignore')

                # Apply refactoring
                # Refactoring modifies file and creates git commit
                git_commit = refactoring.apply(**params)

                if git_commit is None:
                    # Refactoring could not be applied (preconditions failed)
                    logger.debug(f"Refactoring skipped: {refactoring.__class__.__name__}")
                    continue

                # Get validator and optimization level from git_commit
                validator = ValidatorFactory.from_id(git_commit.validator_type)
                optimization_level = validator.get_optimization_level()

                # Compile original (need to restore original content first)
                file_path.write_text(original_content, encoding='utf-8')
                original_compiled = self.compiler.compile_file(
                    file_path,
                    optimization_level=optimization_level
                )

                # Restore modified content and compile
                repo.checkout_file(file_path)  # Restore from git commit
                modified_compiled = self.compiler.compile_file(
                    file_path,
                    optimization_level=optimization_level
                )

                # Validate
                is_valid = validator.validate(original_compiled, modified_compiled)

                if is_valid:
                    # Keep commit
                    accepted_commits.append(git_commit.commit_message)
                    logger.info(f"Accepted: {git_commit.commit_message}")

                    validation_results.append(ValidationResult(
                        file=str(file_path),
                        valid=True
                    ))
                else:
                    # Rollback commit
                    git_commit.rollback()
                    rejected_commits.append(git_commit.commit_message)
                    logger.info(f"Rejected: {git_commit.commit_message}")

                    validation_results.append(ValidationResult(
                        file=str(file_path),
                        valid=False
                    ))

                    # Symbols already invalidated by refactoring, but rollback restored file
                    # Re-invalidate so symbols get refreshed from restored content
                    symbols.invalidate_file(file_path)

            # Determine result status
            if len(accepted_commits) > 0 and len(rejected_commits) == 0:
                status = ResultStatus.SUCCESS
            elif len(accepted_commits) > 0 and len(rejected_commits) > 0:
                status = ResultStatus.PARTIAL
            else:
                status = ResultStatus.FAILED

            # Squash and rebase accepted commits
            if len(accepted_commits) > 0:
                logger.info(f"Squashing {len(accepted_commits)} commits")
                repo.squash_and_rebase(atomic_branch, repo.work_branch)
                repo.push()
            else:
                logger.info("No accepted commits, cleaning up")
                repo.checkout_branch(repo.work_branch)
                repo.delete_branch(atomic_branch, force=True)

            return Result(
                status=status,
                message=mod_instance.get_name(),
                validation_results=validation_results,
                accepted_commits=accepted_commits,
                rejected_commits=rejected_commits
            )

        except Exception as e:
            logger.exception(f"Error during refactoring processing: {e}")
            try:
                repo.checkout_branch(repo.work_branch)
                repo.delete_branch(atomic_branch, force=True)
            except Exception:
                pass
            raise
```

**Key changes:**
- Single code path (no `_process_builtin_mod()`)
- Doxygen required (`_ensure_doxygen_data()`)
- Symbol table loaded once (`_load_symbols()`)
- Refactorings applied in loop, each returns `GitCommit` or `None`
- Validator type comes from `git_commit.validator_type`
- Rollback on validation failure via `git_commit.rollback()`

---

## Migration Checklist

### Phase 1: Core Infrastructure
- [ ] Create `core/git_commit.py` with GitCommit class
- [ ] Create `core/validators/validator_type.py` with ValidatorType constants
- [ ] Create `core/doxygen/symbol_table.py` with SymbolTable class
- [ ] Create `core/refactorings/refactoring_base.py` with RefactoringBase
- [ ] Add `checkout_file()` method to Repo class
- [ ] Add `get_commit_hash()` method to Repo class (if not present)
- [ ] Update `DoxygenParser` with `parse_all_symbols()` method

### Phase 2: Initial Refactorings
- [ ] Create `core/refactorings/add_function_qualifier.py`
- [ ] Create `core/refactorings/remove_function_qualifier.py`
- [ ] Test refactorings in isolation with sample repos

### Phase 3: Update ModProcessor
- [ ] Remove old mod processing logic
- [ ] Add `_ensure_doxygen_data()` method
- [ ] Add `_load_symbols()` method
- [ ] Add `_process_refactorings()` method
- [ ] Update `process_mod()` to use new architecture

### Phase 4: Update BaseMod
- [ ] Remove `get_validator_id()` abstract method
- [ ] Remove `generate_changes()` abstract method
- [ ] Add `generate_refactorings()` abstract method
- [ ] Update `base_mod.py` file

### Phase 5: Migrate All Mods
- [ ] Update `AddOverrideMod` to use refactorings
- [ ] Update `RemoveInlineMod` to use refactorings
- [ ] Update `ReplaceMS_SpecificMod` to use refactorings
- [ ] Update `MS_MacroReplacement` to use refactorings
- [ ] Update any other existing mods

### Phase 6: Testing
- [ ] Update smoke tests in `smoketest.py`
- [ ] Add tests for SymbolTable invalidation/refresh
- [ ] Add tests for GitCommit rollback
- [ ] Test end-to-end with real repositories
- [ ] Verify Doxygen generation on first run
- [ ] Verify no regressions in validation

### Phase 7: Cleanup
- [ ] Remove old mod pattern remnants
- [ ] Update documentation (CLAUDE.md files)
- [ ] Update architecture diagrams if any

---

## Key Design Points Summary

### GitCommit
- **Minimal fields:** repo, commit_message, validator_type, affected_symbols, commit_hash
- **Constructor commits:** GitCommit creation performs actual git commit
- **Rollback support:** `rollback()` method for validation failures
- **No inheritance:** Refactorings return GitCommit, not inherit from it

### RefactoringBase
- **Provides context:** repo and symbols available to all refactorings
- **No abstract apply():** Allows subclasses to use named parameters
- **Helper methods:** Common operations like validator selection
- **Returns GitCommit:** Success returns GitCommit, failure returns None

### SymbolTable
- **Lazy refresh:** Dirty files only refreshed on query
- **File-level invalidation:** Simpler than symbol-level tracking
- **Auto-refresh:** Queries automatically refresh dirty files by default
- **Full Doxygen regeneration:** Simpler implementation

### ModProcessor
- **Single code path:** No separate `_process_builtin_mod()`
- **Doxygen required:** Always ensures Doxygen data exists
- **Type-safe:** No string parameters for mod names
- **Symbol-aware:** SymbolTable passed to all mods

### Folder Structure
- **Flat refactorings/:** All refactorings in single folder
- **Clear separation:** refactorings/ vs mods/ vs validators/
- **Constants separate:** ValidatorType in validators/validator_type.py

### Type Safety
- **No dataclasses:** Regular classes only
- **No string identifiers:** ValidatorType constants instead of strings
- **Type hints:** Use TYPE_CHECKING imports to avoid circular dependencies

---

## Example End-to-End Flow

1. **User submits mod request** via web UI (e.g., "Add Override")
2. **Server converts to ModRequest** object with mod instance
3. **ModProcessor.process_mod()** called:
   - Initialize repo
   - Ensure Doxygen data exists
   - Load SymbolTable
4. **Mod.generate_refactorings()** called:
   - Analyzes symbols to find virtual functions without override
   - Yields (AddFunctionQualifier instance, params) for each
5. **For each refactoring:**
   - ModProcessor saves original file content
   - **Refactoring.apply()** called:
     - Validates preconditions
     - Modifies file in-place
     - Creates git commit
     - Invalidates symbols
     - Returns GitCommit object
   - ModProcessor compiles original and modified
   - ModProcessor validates using validator from GitCommit
   - If valid: keep commit
   - If invalid: rollback via `git_commit.rollback()`
6. **Squash and push** all accepted commits
7. **Return Result** with status and validation details

---

## Advantages of This Architecture

1. **Separation of Concerns**
   - Mods: Planning (what to refactor, where)
   - Refactorings: Execution (how to refactor)
   - Validators: Verification (is it safe)

2. **Reusability**
   - Same refactoring used by multiple mods
   - AddFunctionQualifier handles const, override, noexcept, etc.

3. **Symbol-Aware**
   - Reduces false positives by understanding code structure
   - Mods can query call graphs, inheritance hierarchies, etc.

4. **Type-Safe**
   - No string identifiers in core logic
   - ValidatorType constants prevent typos
   - Enums and objects throughout

5. **Testability**
   - Refactorings testable in isolation
   - Mock SymbolTable for unit tests
   - Clear interfaces between components

6. **Maintainability**
   - Single code path in ModProcessor
   - Consistent pattern across all mods
   - Clear rollback semantics with GitCommit

7. **Extensibility**
   - Easy to add new refactorings
   - Easy to add new mods using existing refactorings
   - Symbol system enables sophisticated analysis

---

## Future Enhancements (Not in Initial Plan)

### Multi-File Refactorings
Current design assumes one commit = one file. For refactorings spanning multiple files:
- GitCommit could track `affected_files: List[Path]`
- Refactorings would modify multiple files before committing
- Validation would compile all affected files

### Refactoring Composition
For complex transformations built from simpler ones:
- Create `CompositeRefactoring` class
- Applies multiple refactorings as single atomic operation
- All-or-nothing commit (rollback if any sub-refactoring fails)

### Incremental Doxygen
To avoid full regeneration on every file change:
- Investigate Doxygen incremental mode
- Parse only changed files from XML
- Update symbol table incrementally

### Refactoring Preconditions
For explicit precondition checking:
- Add `can_apply()` method that doesn't modify files
- Mods can filter candidates before attempting refactoring
- Trade-off: More overhead vs fewer failed attempts

### Validation Caching
For performance optimization:
- Cache compilation results by file content hash
- Skip recompilation if content unchanged
- Significant speedup for large files

---

## End of Plan

This architecture provides a solid foundation for sophisticated C++ code modernization with:
- Zero regression risk through validation
- Symbol-aware refactoring planning
- Type-safe implementation throughout
- Clear separation of concerns
- Extensible design for future enhancements
