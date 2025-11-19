# Module API Reference

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
        validation_results: Optional[List[ValidationResult]] = None
    )
    def to_dict() -> Dict[str, Any]
```

### mod_request.py

```python
class ModSourceType(Enum):
    BUILTIN = "builtin"
    COMMIT = "commit"

@dataclass
class ModRequest:
    id: str
    repo_url: str
    repo_name: str
    source_type: ModSourceType
    description: str
    mod_instance: Optional[object] = None
    commit_hash: Optional[str] = None
    timestamp: Optional[str] = None
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
    def commit(message: str) -> str
    def reset_hard(ref: str = 'HEAD') -> str
    def get_current_branch() -> str
    def get_commit_hash(ref: str = 'HEAD') -> str
    def create_patch(from_ref: str, to_ref: str = 'HEAD') -> str
    def rebase(onto_branch: str) -> str
    def merge(branch: str) -> str
    def stash() -> str
    def stash_pop() -> str
    def push() -> str
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

---

## Mods Package

### mods/base_mod.py

```python
class BaseMod(ABC):
    def __init__(self, mod_id: str, description: str)

    @staticmethod
    @abstractmethod
    def get_id() -> str

    @staticmethod
    @abstractmethod
    def get_name() -> str

    @abstractmethod
    def apply(source_file: Path) -> None

    def validate_before_apply(source_file: Path) -> tuple[bool, str]
    def get_metadata() -> Dict[str, Any]
```

### mods/mod_factory.py

```python
class ModType(Enum):
    REMOVE_INLINE = RemoveInlineMod
    ADD_OVERRIDE = AddOverrideMod
    REPLACE_MS_SPECIFIC = ReplaceMSSpecificMod
    COMMIT = CommitMod

class ModFactory:
    @staticmethod
    def from_id(mod_id: str) -> BaseMod

    @staticmethod
    def get_available_mods() -> List[Dict[str, Any]]
```

### mods/mod_handler.py

```python
class ModHandler:
    def __init__(self)

    def apply_mod_instance(cpp_file: Path, mod_instance: BaseMod) -> Path
    def get_mod_history() -> List[Dict[str, Any]]
```

### mods/remove_inline_mod.py

```python
class RemoveInlineMod(BaseMod):
    @staticmethod
    def get_id() -> str  # Returns 'remove_inline'

    @staticmethod
    def get_name() -> str  # Returns 'Remove Inline Keywords'

    def apply(source_file: Path) -> None
```

### mods/add_override_mod.py

```python
class AddOverrideMod(BaseMod):
    @staticmethod
    def get_id() -> str  # Returns 'add_override'

    @staticmethod
    def get_name() -> str  # Returns 'Add Override Keywords'

    def apply(source_file: Path) -> None
```

### mods/replace_ms_specific_mod.py

```python
class ReplaceMSSpecificMod(BaseMod):
    replacements: Dict[str, str]  # MS-specific -> standard C++

    @staticmethod
    def get_id() -> str  # Returns 'replace_ms_specific'

    @staticmethod
    def get_name() -> str  # Returns 'Replace MS-Specific Syntax'

    def apply(source_file: Path) -> None
```

### mods/commit_mod.py

```python
class CommitMod(BaseMod):
    @staticmethod
    def get_id() -> str  # Returns 'commit'

    @staticmethod
    def get_name() -> str  # Returns 'Validate Commit'

    def apply(source_file: Path) -> None  # No-op for commit validation
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

    @abstractmethod
    def validate(original: CompiledFile, modified: CompiledFile) -> bool
```

### validators/validator_factory.py

```python
class ValidatorType(Enum):
    ASM = ASMValidator
    SOURCE_DIFF = SourceDiffValidator

class ValidatorFactory:
    @staticmethod
    def from_id(validator_id: str, compiler) -> BaseValidator

    @staticmethod
    def get_available_validators() -> List[Dict[str, Any]]
```

### validators/asm_validator.py

```python
class ASMValidator(BaseValidator):
    def __init__(self, compiler)

    @staticmethod
    def get_id() -> str  # Returns 'asm'

    @staticmethod
    def get_name() -> str  # Returns 'Assembly Comparison'

    def validate(original: CompiledFile, modified: CompiledFile) -> bool
```

### validators/source_diff_validator.py

```python
class SourceDiffValidator(BaseValidator):
    def __init__(self, allowed_removals: List[str] = None)

    @staticmethod
    def get_id() -> str  # Returns 'source_diff'

    @staticmethod
    def get_name() -> str  # Returns 'Source Diff'

    def validate(original: CompiledFile, modified: CompiledFile) -> bool
```

---

## Compilers Package

### compilers/base_compiler.py

```python
class BaseCompiler(ABC):
    def __init__(self, compiler_path: str)

    @staticmethod
    @abstractmethod
    def get_id() -> str

    @staticmethod
    @abstractmethod
    def get_name() -> str

    @abstractmethod
    def compile_file(source_file: Path, additional_flags: str = None) -> CompiledFile
```

### compilers/compiler_factory.py

```python
class CompilerType(Enum):
    MSVC = MSVCCompiler

class CompilerFactory:
    @staticmethod
    def from_id(compiler_id: str, compiler_path: str) -> BaseCompiler

    @staticmethod
    def get_available_compilers() -> List[Dict[str, Any]]
```

### compilers/compiler.py

```python
class MSVCCompiler(BaseCompiler):
    default_flags = ['/O2', '/EHsc', '/nologo', '/W3']

    def __init__(self, cl_path: str = None)  # Auto-discovers via vswhere if not provided

    @staticmethod
    def get_id() -> str  # Returns 'msvc'

    @staticmethod
    def get_name() -> str  # Returns 'Microsoft Visual C++'

    def compile_file(source_file: Path, additional_flags: str = None) -> CompiledFile
```

### compilers/compiled_file.py

```python
class CompiledFile:
    source_file: Path
    asm_output: str  # Assembly content as string
```

---

## Server Package

### server/app.py

**Global State:**
```python
mod_queue: queue.Queue  # Queue of ModRequest objects
results: Dict[str, Result]  # Results by mod_id
CONFIG: Dict  # workspace, repos, temp, git_path
```

**Flask Routes:**

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Main UI page |
| `/api/repos` | GET | List all repositories |
| `/api/repos` | POST | Add repository |
| `/api/repos/<repo_id>` | PUT | Update repository |
| `/api/repos/<repo_id>` | DELETE | Delete repository |
| `/api/mods` | POST | Submit mod for processing |
| `/api/mods/<mod_id>/status` | GET | Get mod status |
| `/api/queue/status` | GET | Get queue status |
| `/api/available/mods` | GET | List available mods |
| `/api/available/validators` | GET | List available validators |
| `/api/available/compilers` | GET | List available compilers |

**Worker Thread:**
```python
def mod_worker() -> None
    # Continuously processes ModRequest objects from mod_queue
    # Updates results dict with Result objects
```
