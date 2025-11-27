# LevelUp API Documentation

This document provides comprehensive API documentation for both the HTTP REST API (server interface) and the internal Python module API.

---

## Table of Contents

1. [REST API (Server Interface)](#rest-api-server-interface)
   - [Repository Management](#repository-management)
   - [Mod Management](#mod-management)
   - [Queue Status](#queue-status)
   - [Available Resources](#available-resources)
2. [Python Module API](#python-module-api)
   - [Core Package](#core-package)
   - [Mods Package](#mods-package)
   - [Refactorings Package](#refactorings-package)
   - [Validators Package](#validators-package)
   - [Compilers Package](#compilers-package)

---

# REST API (Server Interface)

Base URL: `/api`

## Repository Management

### `GET /api/repos`
**Description**: Retrieve all configured repositories

**Response**:
```json
[
  {
    "id": "uuid",
    "name": "string",
    "url": "string",
    "post_checkout": "string",
    "build_command": "string",
    "single_tu_command": "string",
    "timestamp": "ISO datetime"
  }
]
```

**Note**: Work branch is hardcoded to "levelup-work" and is not configurable.

### `POST /api/repos`
**Description**: Add a new repository configuration

**Request Body**:
```json
{
  "url": "string (required)",
  "post_checkout": "string (optional)",
  "build_command": "string (optional)",
  "single_tu_command": "string (optional)"
}
```

**Note**: Repository name is automatically extracted from the URL.

**Response**: Same as single repository object above

### `PUT /api/repos/<repo_id>`
**Description**: Update an existing repository configuration

**Request Body**:
```json
{
  "url": "string (optional)",
  "post_checkout": "string (optional)",
  "build_command": "string (optional)",
  "single_tu_command": "string (optional)"
}
```

**Response**: Updated repository object

### `DELETE /api/repos/<repo_id>`
**Description**: Delete a repository configuration

**Response**:
```json
{
  "success": boolean
}
```

---

## Mod Management

### `POST /api/mods`
**Description**: Submit a new mod for processing

**Request Body** (for commit type):
```json
{
  "repo_name": "string (required)",
  "repo_url": "string (required)",
  "type": "commit",
  "commit_hash": "string (required for commit type)",
  "description": "string (required)"
}
```

**Request Body** (for builtin type):
```json
{
  "repo_name": "string (required)",
  "repo_url": "string (required)",
  "type": "builtin",
  "mod_type": "string (required for builtin type)",
  "description": "string (required)"
}
```

**Response**:
```json
{
  "id": "uuid",
  "repo_name": "string",
  "repo_url": "string",
  "type": "string",
  "description": "string",
  "timestamp": "ISO datetime",
  "commit_hash": "string (if type=commit)",
  "mod_type": "string (if type=builtin)"
}
```

### `GET /api/mods/{mod_id}/status`
**Description**: Get the status of a specific mod

**Response**:
```json
{
  "status": "queued|processing|success|partial|failed|error",
  "message": "string",
  "validation_results": [
    {
      "file": "string",
      "valid": boolean
    }
  ],
  "accepted_commits": ["string"],
  "rejected_commits": ["string"],
  "timestamp": "ISO datetime"
}
```

**Status Values**:
- `queued`: Mod is waiting to be processed
- `processing`: Mod is currently being processed
- `success`: All refactorings passed validation
- `partial`: Some refactorings passed validation, some failed
- `failed`: No refactorings passed validation
- `error`: An error occurred during processing

---

## Queue Status

### `GET /api/queue/status`
**Description**: Get overall queue status and all results

**Response**:
```json
{
  "queue_size": integer,
  "results": {
    "mod_id": {
      "status": "string",
      "message": "string",
      "validation_results": [...],
      "timestamp": "string"
    }
  },
  "timestamp": "ISO datetime"
}
```

---

## Available Resources

### `GET /api/available/mods`
**Description**: Get list of available mod types

**Response**:
```json
[
  {
    "id": "remove_inline",
    "name": "Remove Inline Keywords"
  },
  {
    "id": "add_override",
    "name": "Add Override Keywords"
  },
  {
    "id": "replace_ms_specific",
    "name": "Replace MS-Specific Syntax"
  },
  {
    "id": "ms_macro_replacement",
    "name": "MS Macro Replacement"
  }
]
```

### `GET /api/available/validators`
**Description**: Get list of available validator types

**Response**:
```json
[
  {
    "id": "asm_o0",
    "name": "Assembly O0 Comparison"
  },
  {
    "id": "asm_o3",
    "name": "Assembly O3 Comparison"
  }
]
```

### `GET /api/available/compilers`
**Description**: Get list of available compiler types

**Response**:
```json
[
  {
    "id": "msvc",
    "name": "Microsoft Visual C++"
  },
  {
    "id": "clang",
    "name": "Clang"
  }
]
```

**Note**: The `id` field for each resource is stable and should be used when referencing these resources in API requests. The `name` field is human-readable and may change.

---

# Python Module API

## Core Package

### validation_result.py

```python
class ValidationResult:
    def __init__(self, file: str, valid: bool)
    def to_dict() -> Dict[str, Any]
```

### result.py

```python
class ResultStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    ERROR = "error"

class Result:
    def __init__(
        self,
        status: ResultStatus,
        message: str,
        timestamp: Optional[str] = None,
        validation_results: Optional[List[ValidationResult]] = None,
        accepted_commits: Optional[List[str]] = None,
        rejected_commits: Optional[List[str]] = None
    )
    def to_dict() -> Dict[str, Any]
```

### mod_request.py

```python
class ModSourceType(Enum):
    BUILTIN = "builtin"
    COMMIT = "commit"

class ModRequest:
    def __init__(
        self,
        id: str,
        repo_url: str,
        repo_name: str,
        source_type: ModSourceType,
        description: str,
        mod_instance: Optional[object] = None,
        commit_hash: Optional[str] = None,
        timestamp: Optional[str] = None
    )
```

### repo.py

```python
class Repo:
    WORK_BRANCH = "levelup-work"

    def __init__(
        self,
        url: str,
        repos_folder: Path,
        git_path: str = 'git',
        post_checkout: str = ''
    )

    @staticmethod
    def get_repo_name(repo_url: str) -> str

    @classmethod
    def from_config(config: Dict, repos_base_path: Path, git_path: str = 'git') -> Repo

    def clone() -> Repo
    def ensure_cloned() -> None
    def pull() -> str
    def checkout_branch(branch_name: Optional[str] = None, create: bool = False) -> None
    def prepare_work_branch() -> None
    def cherry_pick(commit_hash: str) -> str
    def commit(message: str) -> bool
    def reset_hard(ref: str = 'HEAD') -> str
    def checkout_file(file_path: Path) -> str
    def get_current_branch() -> str
    def get_commit_hash(ref: str = 'HEAD') -> str
    def create_atomic_branch(base_branch: str, atomic_branch_name: str) -> str
    def squash_and_rebase(atomic_branch: str, target_branch: str) -> None
    def delete_branch(branch: str, force: bool = False) -> str
    def push(branch: str = None) -> str
    def generate_doxygen() -> Tuple[Path, Path]
    def get_doxygen_parser() -> Optional[DoxygenParser]
```

### mod_processor.py

```python
class ModProcessor:
    def __init__(
        self,
        repos_path: Path,
        git_path: str = 'git'
    )

    def process_mod(mod_request: ModRequest) -> Result
```

### git_commit.py

```python
class GitCommit:
    def __init__(
        self,
        repo: Repo,
        commit_message: str,
        validator_type: str,  # e.g., "asm_o0", "asm_o3"
        affected_symbols: List[str],  # Qualified symbol names
        probability_of_success: float  # 0.0-1.0, from refactoring's get_probability_of_success()
    )

    def rollback() -> None  # Reverts commit (git reset --hard)
    def to_dict() -> Dict[str, Any]  # Serialize for JSON
```

---

## Mods Package

### mods/base_mod.py

```python
class BaseMod(ABC):
    def __init__(self, mod_id: str, description: str)

    @staticmethod
    @abstractmethod
    def get_id() -> str  # IMPORTANT: Stable identifier used in APIs

    @staticmethod
    @abstractmethod
    def get_name() -> str

    @abstractmethod
    def generate_refactorings(
        self,
        repo: Repo,
        symbols: SymbolTable
    ) -> Generator[Tuple[RefactoringBase, ...], None, None]
        # Yields tuples of (refactoring_instance, *args)
        # Args are passed to refactoring.apply(*args)
        # Example: yield (RemoveFunctionQualifier(repo), symbol, qualifier)

    def get_metadata() -> Dict[str, Any]
```

### mods/mod_factory.py

```python
class ModType(Enum):
    REMOVE_INLINE = RemoveInlineMod
    ADD_OVERRIDE = AddOverrideMod
    REPLACE_MS_SPECIFIC = ReplaceMSSpecificMod
    MS_MACRO_REPLACEMENT = MSMacroReplacementMod

class ModFactory:
    @staticmethod
    def from_id(mod_id: str) -> BaseMod

    @staticmethod
    def get_available_mods() -> List[Dict[str, Any]]
```

### mods/remove_inline_mod.py

```python
class RemoveInlineMod(BaseMod):
    @staticmethod
    def get_id() -> str  # Returns 'remove_inline'

    @staticmethod
    def get_name() -> str  # Returns 'Remove Inline Keywords'

    def generate_refactorings(repo: Repo, symbols: SymbolTable)
        # Yields (refactoring, symbol, qualifier) tuples
        # Example: yield (RemoveFunctionQualifier(repo), symbol, QualifierType.INLINE)
```

### mods/add_override_mod.py

```python
class AddOverrideMod(BaseMod):
    @staticmethod
    def get_id() -> str  # Returns 'add_override'

    @staticmethod
    def get_name() -> str  # Returns 'Add Override Keywords'

    def generate_refactorings(repo: Repo, symbols: SymbolTable)
        # Yields (refactoring, symbol, qualifier) tuples
        # Example: yield (AddFunctionQualifier(repo), symbol, QualifierType.OVERRIDE)
```

---

## Refactorings Package

### refactorings/refactoring_base.py

```python
class RefactoringBase(ABC):
    def __init__(self, repo: Repo)

    @abstractmethod
    def get_probability_of_success() -> float
        # Return 0.0-1.0 indicating confidence
        # High values (0.9) = safe refactorings
        # Low values (0.1) = speculative changes
        # Used for batch validation optimization

    # Subclasses implement apply() with their own named parameters
    # def apply(...) -> Optional[GitCommit]
    # Returns GitCommit on success, None if cannot be applied
```

### refactorings/add_function_qualifier.py

```python
class AddFunctionQualifier(RefactoringBase):
    def get_probability_of_success() -> float  # Returns ~0.7

    def apply(
        self,
        symbol: Symbol,
        qualifier: str
    ) -> Optional[GitCommit]
        # Modifies file in-place, creates git commit
        # Returns GitCommit with validator_type and affected_symbols
        # Returns None if preconditions fail
```

### refactorings/remove_function_qualifier.py

```python
class RemoveFunctionQualifier(RefactoringBase):
    def get_probability_of_success() -> float  # Returns 0.9

    def apply(
        self,
        symbol: Symbol,
        qualifier: str
    ) -> Optional[GitCommit]
        # Modifies file in-place, creates git commit
        # Returns GitCommit with validator_type and affected_symbols
        # Returns None if preconditions fail
```

### refactorings/qualifier_type.py

```python
class QualifierType:
    CONST = "const"
    NOEXCEPT = "noexcept"
    OVERRIDE = "override"
    FINAL = "final"
    CONSTEXPR = "constexpr"
    INLINE = "inline"
    STATIC = "static"
    VIRTUAL = "virtual"
    NODISCARD = "[[nodiscard]]"
    MAYBE_UNUSED = "[[maybe_unused]]"
```

---

## Validators Package

### validators/base_validator.py

```python
class BaseValidator(ABC):
    @staticmethod
    @abstractmethod
    def get_id() -> str

    @staticmethod
    @abstractmethod
    def get_name() -> str

    @staticmethod
    @abstractmethod
    def get_optimization_level() -> int

    @abstractmethod
    def validate(original: CompiledFile, modified: CompiledFile) -> bool
```

### validators/validator_factory.py

```python
class ValidatorType(Enum):
    ASM_O0 = ASMValidatorO0
    ASM_O3 = ASMValidatorO3

class ValidatorFactory:
    @staticmethod
    def from_id(validator_id: str) -> BaseValidator

    @staticmethod
    def get_available_validators() -> List[Dict[str, Any]]
```

### validators/asm_validator.py

```python
class ASMValidatorO0(BaseValidator):
    @staticmethod
    def get_id() -> str  # Returns 'asm_o0'

    @staticmethod
    def get_name() -> str  # Returns 'Assembly O0 Comparison'

    @staticmethod
    def get_optimization_level() -> int  # Returns 0

    def validate(original: CompiledFile, modified: CompiledFile) -> bool


class ASMValidatorO3(BaseValidator):
    @staticmethod
    def get_id() -> str  # Returns 'asm_o3'

    @staticmethod
    def get_name() -> str  # Returns 'Assembly O3 Comparison'

    @staticmethod
    def get_optimization_level() -> int  # Returns 3

    def validate(original: CompiledFile, modified: CompiledFile) -> bool
```

### validators/validator_id.py

```python
class ValidatorId:
    """Constants for validator IDs (prefer over raw strings)."""
    ASM_O0 = "asm_o0"
    ASM_O3 = "asm_o3"
```

---

## Compilers Package

### compilers/base_compiler.py

```python
class BaseCompiler(ABC):
    @staticmethod
    @abstractmethod
    def get_id() -> str

    @staticmethod
    @abstractmethod
    def get_name() -> str

    @abstractmethod
    def compile_file(
        source_file: Path,
        optimization_level: int = 0
    ) -> CompiledFile
```

### compilers/compiler_factory.py

```python
class CompilerType(Enum):
    MSVC = MSVCCompiler
    CLANG = ClangCompiler

def get_compiler() -> BaseCompiler  # Returns configured compiler singleton

def set_compiler(compiler_id: str) -> None  # Change active compiler

class CompilerFactory:
    @staticmethod
    def from_id(compiler_id: str) -> BaseCompiler

    @staticmethod
    def get_available_compilers() -> List[Dict[str, Any]]
```

### compilers/msvc_compiler.py

```python
class MSVCCompiler(BaseCompiler):
    def __init__(self, cl_path: str = None, arch: str = 'x64')
        # Auto-discovers via vswhere if cl_path not provided

    @staticmethod
    def get_id() -> str  # Returns 'msvc'

    @staticmethod
    def get_name() -> str  # Returns 'Microsoft Visual C++'

    def compile_file(
        source_file: Path,
        optimization_level: int = 0
    ) -> CompiledFile
```

### compilers/clang_compiler.py

```python
class ClangCompiler(BaseCompiler):
    def __init__(self, clang_path: str = 'clang')

    @staticmethod
    def get_id() -> str  # Returns 'clang'

    @staticmethod
    def get_name() -> str  # Returns 'Clang'

    def compile_file(
        source_file: Path,
        optimization_level: int = 0
    ) -> CompiledFile
```

### compilers/compiled_file.py

```python
class CompiledFile:
    source_file: Path
    asm_output: str  # Assembly content as string
```

---

## Doxygen Package

### doxygen/symbol_table.py

```python
class SymbolTable:
    def __init__(self, repo: Repo)

    def load_from_doxygen() -> None
    def invalidate_file(file_path: Path) -> None
    def refresh_dirty_files() -> None
    def check_and_refresh_if_stale() -> None

    def get_symbol(qualified_name: str, auto_refresh: bool = True) -> Optional[Symbol]
    def get_symbols_in_file(file_path: Path, auto_refresh: bool = True) -> List[Symbol]
    def get_all_symbols(auto_refresh: bool = True) -> List[Symbol]
```

### doxygen/symbol.py

```python
class SymbolKind:
    FUNCTION = "function"
    CLASS = "class"
    STRUCT = "struct"
    ENUM = "enum"
    TYPEDEF = "typedef"
    VARIABLE = "variable"
    NAMESPACE = "namespace"

class Symbol:
    kind: str
    name: str
    qualified_name: str
    file_path: str
    line_start: int
    line_end: int
    prototype: str
    # ... additional fields
```

---

## Notes

- **String IDs**: All `id` fields in responses are stable and should be used for API calls
- **Type Safety**: Internal code uses enums and type-safe objects; string IDs only at API boundary
- **Validator Types**: Each refactoring specifies which validator to use when creating GitCommit (via ValidatorId constants)
- **Work Branch**: Hardcoded to `"levelup-work"` - not configurable
- **Refactoring Pattern**:
  1. Mods generate refactorings via `generate_refactorings(repo, symbols)` → yields `(refactoring, *args)` tuples
  2. ModProcessor calls `refactoring.apply(*args)` → modifies files and creates GitCommit
  3. Validation using validator specified in GitCommit
  4. Keep commit if valid, rollback if invalid
- **Probability of Success**: Each refactoring reports estimated success probability (0.0-1.0), used for batch validation optimization
- **Symbol Table**: Loaded from Doxygen XML, invalidated per-file after modifications, full refresh on next run if stale
