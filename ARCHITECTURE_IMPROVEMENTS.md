# Architecture Improvements for LevelUp

This document provides concrete recommendations to improve structure, maintainability, and API design with the goal of making APIs **easy to use correctly and difficult to use incorrectly**.

## Current Architecture Analysis

### Strengths
- Type-safe enums (ModSourceType, ResultStatus)
- Factory pattern for extensibility
- Clear package separation (levelup vs levelup_server)
- Abstract base classes for key components
- String IDs only at API boundary

### Weaknesses
- Hard-coded dependencies (tight coupling)
- Broad exception handling without custom types
- Mutable data structures where immutability would be safer
- No dependency injection
- Inconsistent error handling
- Missing validation at boundaries
- Methods that do too much (violate SRP)

---

## Recommendation 1: Protocol-Based Interfaces with Dependency Injection

### Problem
ModProcessor hard-codes dependencies:
```python
def __init__(self, msvc_path: str, repos_path: Path, temp_path: Path, git_path: str = 'git'):
    self.compiler = MSVCCompiler(msvc_path)  # Hard-coded!
    self.asm_validator = ASMValidator(self.compiler)  # Hard-coded!
```

This makes testing difficult and violates Open/Closed Principle.

### Solution: Use Protocol classes (PEP 544) + Dependency Injection

**Create explicit protocols:**
```python
# levelup/interfaces.py
from typing import Protocol, runtime_checkable
from pathlib import Path

@runtime_checkable
class ICompiler(Protocol):
    def compile_to_asm(self, source_file: Path, asm_output_file: Path) -> Path: ...
    def check_syntax(self, source_file: Path) -> tuple[bool, str]: ...

@runtime_checkable
class IValidator(Protocol):
    def validate(self, original_file: Path, modified_file: Path) -> bool: ...
    def get_diff_report(self, original_file: Path, modified_file: Path) -> str: ...

@runtime_checkable
class IModHandler(Protocol):
    def apply_mod_instance(self, cpp_file: Path, mod_instance) -> Path: ...
```

**Inject dependencies:**
```python
class ModProcessor:
    def __init__(
        self,
        compiler: ICompiler,
        validator: IValidator,
        mod_handler: IModHandler,
        repos_path: Path,
        temp_path: Path
    ):
        self.compiler = compiler
        self.validator = validator
        self.mod_handler = mod_handler
        self.repos_path = Path(repos_path)
        self.temp_path = Path(temp_path)
```

**Benefits:**
- Easy to test (inject mocks)
- Can swap implementations without changing ModProcessor
- Type checking ensures compatibility
- Clear contracts

---

## Recommendation 2: Custom Exception Hierarchy

### Problem
Broad exception catching loses context:
```python
except Exception as e:
    return Result(status=ResultStatus.ERROR, message=str(e))
```

### Solution: Domain-specific exceptions

```python
# levelup/exceptions.py
class LevelUpError(Exception):
    """Base exception for all LevelUp errors"""
    pass

class CompilationError(LevelUpError):
    """Compilation failed"""
    def __init__(self, source_file: Path, stderr: str):
        self.source_file = source_file
        self.stderr = stderr
        super().__init__(f"Compilation failed for {source_file}")

class ValidationError(LevelUpError):
    """Validation failed"""
    def __init__(self, reason: str, diff: str = ""):
        self.reason = reason
        self.diff = diff
        super().__init__(f"Validation failed: {reason}")

class GitOperationError(LevelUpError):
    """Git operation failed"""
    def __init__(self, operation: str, returncode: int, stderr: str):
        self.operation = operation
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Git {operation} failed with code {returncode}")

class ModApplicationError(LevelUpError):
    """Mod application failed"""
    pass

class ConfigurationError(LevelUpError):
    """Invalid configuration"""
    pass
```

**Usage:**
```python
def compile_to_asm(self, source_file, asm_output_file):
    result = self._run_cl(args, cwd=source_file.parent)

    if result.returncode != 0:
        raise CompilationError(source_file, result.stderr)

    if not Path(asm_output_file).exists():
        raise CompilationError(source_file, "ASM file not generated")

    return Path(asm_output_file)
```

**Benefits:**
- Specific error types can be caught and handled appropriately
- Rich error context (structured data, not just strings)
- Clear error boundaries
- Better logging and debugging

---

## Recommendation 3: Immutable Data Structures

### Problem
Result and ModRequest can be mutated after creation:
```python
result = Result(status=ResultStatus.QUEUED, ...)
# Later someone could do:
result.status = "processing"  # String instead of enum!
result.validation_results.append(...)  # Mutation!
```

### Solution: Use frozen dataclasses

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass(frozen=True)
class ValidationResult:
    """Single file validation result - immutable"""
    file_path: Path
    is_valid: bool
    validator_type: str
    diff_report: Optional[str] = None
    error_message: Optional[str] = None

@dataclass(frozen=True)
class Result:
    """Immutable result object"""
    status: ResultStatus
    message: str
    timestamp: str
    validation_results: tuple[ValidationResult, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if not isinstance(self.status, ResultStatus):
            raise TypeError(f"status must be ResultStatus enum, got {type(self.status)}")

    def with_status(self, new_status: ResultStatus, new_message: str = None) -> 'Result':
        """Return new Result with updated status (immutable update)"""
        return Result(
            status=new_status,
            message=new_message or self.message,
            timestamp=self.timestamp,
            validation_results=self.validation_results
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'message': self.message,
            'timestamp': self.timestamp,
            'validation_results': [
                {
                    'file': str(vr.file_path),
                    'valid': vr.is_valid,
                    'validator_type': vr.validator_type,
                    'diff_report': vr.diff_report,
                    'error_message': vr.error_message
                }
                for vr in self.validation_results
            ]
        }
```

**Benefits:**
- Cannot accidentally mutate state
- Thread-safe by default
- Clear update semantics (create new instance)
- Hashable (can use as dict keys)

---

## Recommendation 4: Builder Pattern for Complex Objects

### Problem
ModRequest has many optional fields with complex validation:
```python
ModRequest(
    id=..., repo_url=..., repo_name=..., work_branch=...,
    source_type=..., description=..., mod_instance=...,
    commit_hash=None, patch_path=None, allow_reorder=False
)
# Easy to forget required fields or pass wrong combinations
```

### Solution: Builder pattern

```python
# levelup/mod_request.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

@dataclass(frozen=True)
class ModRequest:
    id: str
    repo_url: str
    repo_name: str
    work_branch: str
    source_type: ModSourceType
    description: str
    mod_instance: Optional[BaseMod] = None  # Type-safe!
    commit_hash: Optional[str] = None
    patch_path: Optional[Path] = None
    allow_reorder: bool = False
    timestamp: str = ""

class ModRequestBuilder:
    """Builder for ModRequest - makes it impossible to create invalid requests"""

    def __init__(self, request_id: str, repo_url: str, work_branch: str):
        self._id = request_id
        self._repo_url = repo_url
        self._repo_name = Repo.get_repo_name(repo_url)
        self._work_branch = work_branch
        self._description = ""
        self._timestamp = datetime.now().isoformat()

    def with_builtin_mod(self, mod_instance: BaseMod, description: str = "") -> ModRequest:
        """Create BUILTIN mod request - enforces correct fields at compile time"""
        return ModRequest(
            id=self._id,
            repo_url=self._repo_url,
            repo_name=self._repo_name,
            work_branch=self._work_branch,
            source_type=ModSourceType.BUILTIN,
            description=description or f"Apply {mod_instance.get_name()}",
            mod_instance=mod_instance,
            timestamp=self._timestamp
        )

    def with_commit(self, commit_hash: str, description: str = "") -> ModRequest:
        """Create COMMIT mod request - enforces correct fields at compile time"""
        if not commit_hash:
            raise ValueError("commit_hash cannot be empty")

        return ModRequest(
            id=self._id,
            repo_url=self._repo_url,
            repo_name=self._repo_name,
            work_branch=self._work_branch,
            source_type=ModSourceType.COMMIT,
            description=description or f"Cherry-pick commit {commit_hash[:8]}",
            commit_hash=commit_hash,
            timestamp=self._timestamp
        )

    def with_patch(self, patch_path: Path, description: str = "") -> ModRequest:
        """Create PATCH mod request - enforces correct fields at compile time"""
        if not patch_path.exists():
            raise FileNotFoundError(f"Patch file not found: {patch_path}")

        return ModRequest(
            id=self._id,
            repo_url=self._repo_url,
            repo_name=self._repo_name,
            work_branch=self._work_branch,
            source_type=ModSourceType.PATCH,
            description=description or f"Apply patch {patch_path.name}",
            patch_path=patch_path,
            timestamp=self._timestamp
        )
```

**Usage:**
```python
# In app.py - impossible to create invalid requests!
builder = ModRequestBuilder(mod_id, data['repo_url'], data['work_branch'])

if data['type'] == 'builtin':
    mod_instance = ModFactory.from_id(data['mod_type'])
    mod_request = builder.with_builtin_mod(mod_instance)
elif data['type'] == 'commit':
    mod_request = builder.with_commit(data['commit_hash'])
elif data['type'] == 'patch':
    mod_request = builder.with_patch(Path(data['patch_path']))
```

**Benefits:**
- Impossible to create invalid combinations
- Type-safe at compile time
- Clear intent (method names document usage)
- Validation happens at construction

---

## Recommendation 5: Context Managers for Resource Management

### Problem
Temporary files and subprocess calls lack guaranteed cleanup:
```python
# What if compilation fails? Who cleans up temp files?
original_asm = self.compiler.compile_to_asm(cpp_file, self.temp_path / f'original_{cpp_file.stem}.asm')
```

### Solution: Context managers

```python
# levelup/utils/temp_workspace.py
from contextlib import contextmanager
from pathlib import Path
import tempfile
import shutil

@contextmanager
def temporary_workspace(base_path: Path):
    """Create temporary workspace, guaranteed cleanup"""
    temp_dir = Path(tempfile.mkdtemp(dir=base_path, prefix="levelup_"))
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@contextmanager
def compilation_workspace(compiler: ICompiler, source_file: Path, base_path: Path):
    """Compile with automatic cleanup"""
    with temporary_workspace(base_path) as workspace:
        asm_file = workspace / f"{source_file.stem}.asm"
        try:
            result_path = compiler.compile_to_asm(source_file, asm_file)
            yield result_path
        except CompilationError:
            raise
```

**Usage:**
```python
def validate_file(self, cpp_file: Path) -> ValidationResult:
    with compilation_workspace(self.compiler, cpp_file, self.temp_path) as original_asm:
        # Apply mod
        modified_cpp = self.mod_handler.apply_mod_instance(cpp_file, mod)

        with compilation_workspace(self.compiler, modified_cpp, self.temp_path) as modified_asm:
            is_valid = self.validator.validate(original_asm, modified_asm)

            return ValidationResult(
                file_path=cpp_file,
                is_valid=is_valid,
                validator_type=self.validator.get_name()
            )
    # Temp files automatically cleaned up!
```

**Benefits:**
- Guaranteed cleanup even on exceptions
- Clear resource lifecycle
- No leaked temporary files
- Exception-safe

---

## Recommendation 6: Configuration Object with Validation

### Problem
Global CONFIG dict, no validation:
```python
CONFIG = {
    'workspace': Path('workspace'),
    'msvc_path': os.environ.get('MSVC_PATH', 'cl.exe'),
}
# What if paths don't exist? What if MSVC_PATH is invalid?
```

### Solution: Validated configuration dataclass

```python
# levelup/config.py
from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Optional

@dataclass(frozen=True)
class LevelUpConfig:
    """Validated configuration - construction fails if invalid"""
    workspace: Path
    repos_path: Path
    temp_path: Path
    msvc_path: Path
    git_path: Path

    def __post_init__(self):
        # Validate paths
        for path in [self.workspace, self.repos_path, self.temp_path]:
            if not path.exists():
                raise ConfigurationError(f"Directory does not exist: {path}")

        # Validate executables exist
        if not shutil.which(str(self.msvc_path)) and not self.msvc_path.exists():
            raise ConfigurationError(f"MSVC compiler not found: {self.msvc_path}")

        if not shutil.which(str(self.git_path)):
            raise ConfigurationError(f"Git executable not found: {self.git_path}")

    @classmethod
    def from_environment(cls, workspace: Path = Path('workspace')) -> 'LevelUpConfig':
        """Create config from environment with sensible defaults"""
        workspace = workspace.resolve()
        workspace.mkdir(parents=True, exist_ok=True)

        repos_path = workspace / 'repos'
        repos_path.mkdir(parents=True, exist_ok=True)

        temp_path = workspace / 'temp'
        temp_path.mkdir(parents=True, exist_ok=True)

        msvc_path = Path(os.environ.get('MSVC_PATH', 'cl.exe'))
        git_path = Path(os.environ.get('GIT_PATH', 'git'))

        return cls(
            workspace=workspace,
            repos_path=repos_path,
            temp_path=temp_path,
            msvc_path=msvc_path,
            git_path=git_path
        )
```

**Usage:**
```python
# In app.py - fails early if misconfigured
try:
    config = LevelUpConfig.from_environment()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)

# Pass config to components (dependency injection)
processor = create_mod_processor(config)
```

**Benefits:**
- Fail early (at startup, not during processing)
- Clear error messages
- Immutable (can't accidentally change config)
- Testable (inject test configs)

---

## Recommendation 7: Separate Concerns - Pipeline Pattern

### Problem
`process_mod` does everything (90+ lines):
- Git operations
- File discovery
- Compilation
- Validation
- Committing

Hard to test, hard to reason about, violates SRP.

### Solution: Pipeline of small, focused components

```python
# levelup/pipeline.py
from dataclasses import dataclass
from typing import List, Callable
from pathlib import Path

@dataclass(frozen=True)
class ProcessingContext:
    """Immutable context passed through pipeline"""
    mod_request: ModRequest
    repo: Repo
    cpp_files: tuple[Path, ...]
    temp_workspace: Path

class PipelineStage:
    """Base class for pipeline stages"""
    def __init__(self, name: str):
        self.name = name

    def execute(self, context: ProcessingContext) -> ProcessingContext:
        """Execute stage, return updated context"""
        raise NotImplementedError

class PrepareRepoStage(PipelineStage):
    def __init__(self, repos_path: Path, git_path: str):
        super().__init__("PrepareRepo")
        self.repos_path = repos_path
        self.git_path = git_path

    def execute(self, context: ProcessingContext) -> ProcessingContext:
        repo = Repo(
            url=context.mod_request.repo_url,
            work_branch=context.mod_request.work_branch,
            repo_path=self.repos_path / secure_filename(context.mod_request.repo_name),
            git_path=self.git_path
        )
        repo.ensure_cloned()
        repo.prepare_work_branch()

        return ProcessingContext(
            mod_request=context.mod_request,
            repo=repo,
            cpp_files=context.cpp_files,
            temp_workspace=context.temp_workspace
        )

class ApplyModStage(PipelineStage):
    def execute(self, context: ProcessingContext) -> ProcessingContext:
        repo = context.repo
        request = context.mod_request

        if request.source_type == ModSourceType.COMMIT:
            repo.cherry_pick(request.commit_hash)
        elif request.source_type == ModSourceType.PATCH:
            repo.apply_patch(request.patch_path)
        # BUILTIN mods applied per-file in validation stage

        return context

class DiscoverFilesStage(PipelineStage):
    def execute(self, context: ProcessingContext) -> ProcessingContext:
        cpp_files = tuple(context.repo.repo_path.glob('**/*.cpp'))

        return ProcessingContext(
            mod_request=context.mod_request,
            repo=context.repo,
            cpp_files=cpp_files,
            temp_workspace=context.temp_workspace
        )

class ValidateFilesStage(PipelineStage):
    def __init__(self, compiler: ICompiler, validator: IValidator, mod_handler: IModHandler):
        super().__init__("ValidateFiles")
        self.compiler = compiler
        self.validator = validator
        self.mod_handler = mod_handler

    def execute(self, context: ProcessingContext) -> ProcessingContext:
        # Validation logic here (per-file)
        # Returns context with validation_results
        ...

class CommitChangesStage(PipelineStage):
    def execute(self, context: ProcessingContext) -> ProcessingContext:
        # Only runs if all validations passed
        context.repo.commit(f"LevelUp: {context.mod_request.description}")
        return context

class ModProcessingPipeline:
    """Pipeline orchestrator"""
    def __init__(self, stages: List[PipelineStage]):
        self.stages = stages

    def execute(self, mod_request: ModRequest) -> Result:
        context = ProcessingContext(
            mod_request=mod_request,
            repo=None,
            cpp_files=tuple(),
            temp_workspace=None
        )

        try:
            for stage in self.stages:
                context = stage.execute(context)

            return Result(
                status=ResultStatus.SUCCESS,
                message="Processing completed successfully",
                timestamp=datetime.now().isoformat(),
                validation_results=tuple()  # From context
            )

        except LevelUpError as e:
            return Result(
                status=ResultStatus.ERROR,
                message=str(e),
                timestamp=datetime.now().isoformat()
            )
```

**Usage:**
```python
# Build pipeline
pipeline = ModProcessingPipeline([
    PrepareRepoStage(config.repos_path, str(config.git_path)),
    DiscoverFilesStage(),
    ApplyModStage(),
    ValidateFilesStage(compiler, validator, mod_handler),
    CommitChangesStage()
])

# Execute
result = pipeline.execute(mod_request)
```

**Benefits:**
- Each stage has single responsibility
- Easy to test stages independently
- Can add/remove/reorder stages
- Clear data flow
- Can add logging/metrics per stage

---

## Recommendation 8: Type-Safe Validation Results

### Problem
```python
validation_results = []
validation_results.append({'file': str(cpp_file), 'valid': is_valid})
# Dict[str, Any] - no type safety!
```

### Solution: Proper types

```python
from typing import List
from enum import Enum

class ValidationStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    ERROR = "error"
    SKIPPED = "skipped"

@dataclass(frozen=True)
class ValidationResult:
    file_path: Path
    status: ValidationStatus
    validator_name: str
    original_asm_path: Optional[Path] = None
    modified_asm_path: Optional[Path] = None
    diff_report: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return self.status == ValidationStatus.VALID

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file': str(self.file_path),
            'status': self.status.value,
            'validator': self.validator_name,
            'diff_report': self.diff_report,
            'error': self.error_message
        }

@dataclass(frozen=True)
class ValidationSummary:
    """Summary of all validations"""
    results: tuple[ValidationResult, ...]
    total_files: int
    valid_count: int
    invalid_count: int
    error_count: int

    @classmethod
    def from_results(cls, results: List[ValidationResult]) -> 'ValidationSummary':
        return cls(
            results=tuple(results),
            total_files=len(results),
            valid_count=sum(1 for r in results if r.status == ValidationStatus.VALID),
            invalid_count=sum(1 for r in results if r.status == ValidationStatus.INVALID),
            error_count=sum(1 for r in results if r.status == ValidationStatus.ERROR)
        )

    @property
    def all_valid(self) -> bool:
        return self.invalid_count == 0 and self.error_count == 0
```

**Benefits:**
- Type-safe throughout codebase
- Clear status values (enum)
- Rich information for debugging
- Immutable

---

## Recommendation 9: Repository as Context Manager

### Problem
Repo state changes (checkout, modifications) but no guarantee of cleanup:
```python
repo.prepare_work_branch()
# ... do stuff ...
# What if exception? Branch left in bad state
```

### Solution: Context manager for safe operations

```python
from contextlib import contextmanager

class Repo:
    # ... existing code ...

    @contextmanager
    def work_context(self):
        """Context manager for safe repo operations"""
        original_branch = self.get_current_branch()
        try:
            self.prepare_work_branch()
            yield self
        except Exception:
            # Rollback on error
            self.reset_hard()
            self.checkout_branch(original_branch)
            raise

    @contextmanager
    def transactional_changes(self, commit_message: str):
        """Context manager for transactional changes - auto-commit or rollback"""
        original_commit = self.get_commit_hash()
        try:
            yield self
            # Success - commit changes
            self.commit(commit_message)
        except Exception:
            # Error - rollback
            self.reset_hard(original_commit)
            raise
```

**Usage:**
```python
with repo.work_context():
    # Apply changes
    repo.cherry_pick(commit_hash)

    with repo.transactional_changes(f"LevelUp: {description}"):
        # Validate changes
        if not validate_all():
            raise ValidationError("Validation failed")
        # Auto-commits on success, rollback on exception
```

**Benefits:**
- Guaranteed cleanup
- Clear transaction boundaries
- Exception-safe
- Prevents leaving repo in bad state

---

## Recommendation 10: Input Validation at Boundaries

### Problem
User input from API not validated before processing:
```python
data = request.json
mod_id = str(uuid.uuid4())
# What if data is missing required fields?
```

### Solution: Pydantic or dataclass validation

```python
# levelup_server/schemas.py
from pydantic import BaseModel, validator, Field
from typing import Optional

class CreateRepoRequest(BaseModel):
    url: str = Field(..., min_length=1, description="Git repository URL")
    work_branch: str = Field(..., min_length=1, description="Work branch name")
    post_checkout: Optional[str] = Field("", description="Post-checkout commands")
    build_command: Optional[str] = Field("", description="Build command")
    single_tu_command: Optional[str] = Field("", description="Single TU build command")

    @validator('url')
    def validate_url(cls, v):
        # Validate URL format
        if not (v.startswith('http://') or v.startswith('https://') or v.startswith('git@')):
            raise ValueError('Invalid git URL format')
        return v

    @validator('work_branch')
    def validate_branch_name(cls, v):
        # Validate branch name (no spaces, etc.)
        if ' ' in v:
            raise ValueError('Branch name cannot contain spaces')
        return v

class CreateModRequest(BaseModel):
    type: str = Field(..., description="Mod type: builtin, commit, or patch")
    repo_url: str = Field(..., min_length=1)
    work_branch: str = Field(..., min_length=1)

    # Type-specific fields
    mod_type: Optional[str] = None
    commit_hash: Optional[str] = None
    patch_file: Optional[str] = None

    @validator('type')
    def validate_type(cls, v):
        if v not in ['builtin', 'commit', 'patch']:
            raise ValueError(f'Invalid type: {v}')
        return v

    @validator('commit_hash')
    def validate_commit_hash(cls, v, values):
        if values.get('type') == 'commit' and not v:
            raise ValueError('commit_hash required for commit type')
        if v and len(v) < 7:
            raise ValueError('Invalid commit hash format')
        return v
```

**Usage in API:**
```python
@app.route('/api/repos', methods=['POST'])
def create_repo():
    try:
        # Validate input
        request_data = CreateRepoRequest(**request.json)

        # Build repo config from validated data
        repo_config = build_repo_config(request_data)
        save_repo_config(repo_config)

        return jsonify(repo_config)

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
```

**Benefits:**
- Fail fast with clear error messages
- Type-safe from API to core
- Automatic validation
- Self-documenting API

---

## Summary: Implementation Priority

### Phase 1 - Foundation (High Priority)
1. **Custom exception hierarchy** - Start using immediately
2. **Configuration validation** - Fail early on misconfiguration
3. **Input validation at API boundaries** - Prevent invalid requests

### Phase 2 - Safety (Medium Priority)
4. **Immutable data structures** - Prevent accidental mutations
5. **Context managers** - Resource cleanup and transactions
6. **Type-safe validation results** - Replace dicts with proper types

### Phase 3 - Architecture (Lower Priority, Bigger Changes)
7. **Protocol-based interfaces** - Better testability
8. **Builder pattern** - Safer object construction
9. **Pipeline pattern** - Separation of concerns
10. **Repository context managers** - Transactional git operations

---

## Migration Strategy

Each improvement can be adopted incrementally:

1. **Add new patterns alongside existing code** - Don't rewrite everything
2. **Use new patterns for new features** - Prove value before migration
3. **Gradually migrate critical paths** - Start with most error-prone areas
4. **Keep old interfaces as facades** - Maintain backward compatibility during transition
5. **Add comprehensive tests** - Ensure refactoring doesn't break functionality

---

## Example: End-to-End with All Improvements

```python
# levelup_server/app.py
@app.route('/api/mods', methods=['POST'])
def submit_mod():
    try:
        # 1. Validate input at boundary
        request_data = CreateModRequest(**request.json)

        # 2. Build type-safe request using builder
        mod_id = str(uuid.uuid4())
        builder = ModRequestBuilder(mod_id, request_data.repo_url, request_data.work_branch)

        if request_data.type == 'builtin':
            mod_instance = ModFactory.from_id(request_data.mod_type)
            mod_request = builder.with_builtin_mod(mod_instance)
        elif request_data.type == 'commit':
            mod_request = builder.with_commit(request_data.commit_hash)
        else:
            mod_request = builder.with_patch(Path(request_data.patch_file))

        # 3. Create immutable initial result
        results[mod_id] = Result(
            status=ResultStatus.QUEUED,
            message='Mod queued for processing',
            timestamp=datetime.now().isoformat()
        )

        # 4. Queue for processing
        mod_queue.put(mod_request)

        return jsonify({'mod_id': mod_id})

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except ConfigurationError as e:
        return jsonify({'error': str(e)}), 500

# Worker thread
def mod_worker():
    # Dependency injection
    config = LevelUpConfig.from_environment()
    compiler = MSVCCompiler(str(config.msvc_path))
    validator = ASMValidator(compiler)
    mod_handler = ModHandler()

    # Build pipeline
    pipeline = ModProcessingPipeline([
        PrepareRepoStage(config.repos_path, str(config.git_path)),
        DiscoverFilesStage(),
        ApplyModStage(),
        ValidateFilesStage(compiler, validator, mod_handler),
        CommitChangesStage()
    ])

    while True:
        try:
            mod_request = mod_queue.get(timeout=1)

            # Update to processing
            results[mod_request.id] = results[mod_request.id].with_status(
                ResultStatus.PROCESSING,
                "Processing mod..."
            )

            # Execute pipeline
            result = pipeline.execute(mod_request)

            # Update with final result
            results[mod_request.id] = result

            mod_queue.task_done()

        except queue.Empty:
            continue
        except LevelUpError as e:
            # Domain-specific error handling
            logger.error(f"Processing error: {e}")
            results[mod_request.id] = Result(
                status=ResultStatus.ERROR,
                message=str(e),
                timestamp=datetime.now().isoformat()
            )
```

---

## Conclusion

These improvements create APIs that are:

- **Easy to use correctly**: Builder patterns, validation, type safety
- **Difficult to use incorrectly**: Immutability, protocols, compile-time checks
- **Maintainable**: Separation of concerns, dependency injection
- **Testable**: Protocol interfaces, dependency injection
- **Robust**: Exception hierarchy, context managers, validation

Start with high-priority items and incrementally adopt patterns that provide the most value for your use cases.
